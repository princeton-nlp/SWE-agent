import asyncio
import json
import re
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from swerex.runtime.abstract import Command as RexCommand
from swerex.runtime.abstract import UploadRequest
from typing_extensions import Self

from sweagent.environment.swe_env import SWEEnv
from sweagent.tools.bundle import Bundle
from sweagent.tools.commands import BASH_COMMAND, Command
from sweagent.tools.parsing import FunctionCallingParser, JsonParser, ParseFunction
from sweagent.tools.utils import _guard_multiline_input, generate_command_docs
from sweagent.utils.log import get_logger


class ToolFilterConfig(BaseModel):
    blocklist_error_template: str = "Interactive operation '{action}' is not supported by this environment."
    blocklist: list[str] = [
        "vim",
        "vi",
        "emacs",
        "nano",
        "nohup",
        "git",
        "gdb",
        "less",
    ]
    blocklist_standalone: list[str] = [
        "python",
        "python3",
        "ipython",
        "bash",
        "sh",
        "/bin/bash",
        "/bin/sh",
        "nohup",
        "vi",
        "vim",
        "emacs",
        "nano",
        "su",
    ]
    # todo: probably rename this
    block_unless_regex: dict[str, str] = {
        "radare2": r"\b(?:radare2)\b.*\s+-c\s+.*",
        "r2": r"\b(?:radare2)\b.*\s+-c\s+.*",
    }


class ToolConfig(BaseModel):
    filter: ToolFilterConfig = ToolFilterConfig()
    bundles: list[Bundle] = Field(default_factory=list)

    env_variables: dict[str, Any] = {}
    """Shorthand to set environment variables for the tools, effectively
    equivalent to adding `export VARNAME=value` to the `reset_commands`.
    """

    submit_command: str = "submit"

    parse_function: ParseFunction = Field(default_factory=FunctionCallingParser)

    enable_bash_tool: bool = True

    format_error_template: str = None  # type: ignore
    """Defaults to format_error_template in ParseFunction"""

    command_docs: str = None  # type: ignore
    multi_line_command_endings: dict[str, str] = {}
    submit_command_end_name: str | None = None

    """Commands to install dependencies and tools.
    These commands are executed in a subprocess and are not part of the environment state.
    """

    reset_commands: list[str | list[str]] = []
    """Commands to reset the environment. They will also be called when we start the environment.
    Unlike `install_commands`, these commands are part of the environment state.
    """

    execution_timeout: int = 30
    """Timeout for executing commands in the environment"""

    install_timeout: int = 300
    """Timeout used for each of the installation commands"""

    @cached_property
    def use_function_calling(self) -> bool:
        return isinstance(self.parse_function, FunctionCallingParser)

    @cached_property
    def state_commands(self) -> list[str]:
        return [bundle.state_command for bundle in self.bundles if bundle.state_command]

    # todo: move to ToolHandler?
    @cached_property
    def commands(self) -> list[Command]:
        """Read command files and return parsed command objects"""
        commands = []
        tool_sources: dict[str, Path] = {}  # Track which file each tool comes from
        # Add bash command if enabled
        if self.enable_bash_tool:
            commands.append(BASH_COMMAND)
            tool_sources[BASH_COMMAND.name] = Path("<builtin>")

        # Collect commands from all bundles
        for bundle in self.bundles:
            for command in bundle.commands:
                if command.name in tool_sources:
                    existing_source = tool_sources[command.name]
                    msg = (
                        f"Tool '{command.name}' is defined multiple times:\n"
                        f"  - First definition in: {existing_source}\n"
                        f"  - Duplicate definition in: {bundle.path}"
                    )
                    raise ValueError(msg)
                commands.append(command)
                tool_sources[command.name] = bundle.path

        return commands

    @cached_property
    def tools(self) -> list[dict]:
        return [command.get_function_calling_tool() for command in self.commands]

    # todo: can some of these be moved to ToolHandler?
    def model_post_init(self, __context):
        # for caching:
        commands = self.commands
        multi_line_command_endings = {
            command.name: command.end_name for command in commands if command.end_name is not None
        }
        self.tools

        # assert not self.enable_bash_tool and parse_function is FunctionCallingParser or JsonParser
        if not self.enable_bash_tool and not (
            isinstance(self.parse_function, FunctionCallingParser) or isinstance(self.parse_function, JsonParser)
        ):
            msg = f"Bash tool can only be disabled if {FunctionCallingParser.type} parser or {JsonParser.type} parser is used."
            raise ValueError(msg)

        self.multi_line_command_endings = multi_line_command_endings
        self.command_docs = generate_command_docs(
            self.commands,
            [],
            **self.env_variables,
        )
        if self.format_error_template is None:
            self.format_error_template = self.parse_function.format_error_template
        self.format_error_template = self.format_error_template.format(**self.__dict__)
        for command in commands:
            if command.name == self.submit_command:
                self.submit_command_end_name = command.end_name
                break


class ToolHandler:
    def __init__(self, tools: ToolConfig):
        """This class handles most of the tool usage. It has the following responsibilities:

        - Install the tools
        - Parse commands and handle multiline commands
        - Decide if an action should be blocked
        - Get the current state of the environment
        """
        self.config = tools
        # partially initialized in `install_commands`.
        self._reset_commands = []
        self._command_patterns = self._get_command_patterns()
        self.logger = get_logger("swea-tools", emoji="🧰")
        # For testing: Return this state instead of querying the environment
        self.mock_state: dict[str, str] | None = None

    @classmethod
    def from_config(cls, config: ToolConfig) -> Self:
        return cls(config)

    # Installation & Reset
    # --------------------

    def install(self, env: SWEEnv) -> None:
        self._install_commands(env)
        self.reset(env)

    def reset(self, env: SWEEnv) -> None:
        self.logger.info("Resetting tools")
        self._set_env_variables(env)
        env.communicate(" && ".join(self._reset_commands), check=True, timeout=self.config.install_timeout)

    async def _upload_bundles(self, env: SWEEnv) -> None:
        await asyncio.gather(
            *(
                env.deployment.runtime.upload(
                    UploadRequest(source_path=bundle.path.as_posix(), target_path=f"/root/tools/{bundle.path.name}")
                )
                for bundle in self.config.bundles
            )
        )

    def _install_commands(self, env: SWEEnv) -> None:
        """Make sure all commands are available in the container"""
        self._set_env_variables(env)
        cwd = env.communicate("pwd", check=True).strip()
        asyncio.run(self._upload_bundles(env))
        for bundle in self.config.bundles:
            env.communicate(f"export PATH=$PATH:/root/tools/{bundle.path.name}/bin", check=True)
            asyncio.run(
                env.deployment.runtime.execute(
                    RexCommand(command=f"chmod +x /root/tools/{bundle.path.name}/bin/*", shell=True, check=False)
                )
            )  # check false because bin might not exist
            if (bundle.path / "install.sh").exists():
                env.communicate(
                    f"cd /root/tools/{bundle.path.name}; source install.sh",
                    check=True,
                    timeout=self.config.install_timeout,
                )
            # always make all files in bin executable
            asyncio.run(
                env.deployment.runtime.execute(
                    RexCommand(command=f"chmod +x /root/tools/{bundle.path.name}/bin/*", shell=True, check=True)
                )
            )
        env.communicate(f"cd {cwd}", check=True)
        # check that all commands are available
        missing_tools = []
        for command in self.config.commands:
            try:
                env.communicate(f"which {command.name}", check=True)
            except Exception:
                missing_tools.append(command.name)
        if missing_tools:
            msg = (
                f"The following tools were included in the tool config but are not available in the container: "
                f"{missing_tools}. Please review the tool configs."
            )
            raise RuntimeError(msg)

    def _set_env_variables(self, env: SWEEnv) -> None:
        _env_setters = [f"export {k}={v}" for k, v in self.config.env_variables.items()]
        command = " && ".join(_env_setters)
        env.communicate(command, check=True)

    # Getting state
    # -------------

    def _get_state(self, state_command: str, env: SWEEnv) -> dict[str, str]:
        output = env.communicate(state_command, check=True).strip()
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            msg = f"State {output!r} is not valid json. This is an internal error, please report it."
            raise ValueError(msg) from e

    def get_state(self, env: SWEEnv) -> dict[str, str]:
        """Execute state commands from all bundles and combine their results.
        This can be used to extract environment variables etc. from the environment.
        """
        if self.mock_state is not None:
            return self.mock_state

        combined_state = {}
        for state_command in self.config.state_commands:
            state = self._get_state(state_command, env)
            combined_state.update(state)
        self.logger.debug(f"Retrieved state from environment: {combined_state}")
        return combined_state

    # Blocking
    # --------

    def should_block_action(self, action: str) -> bool:
        """Check if the command should be blocked."""
        names = action.strip().split()
        if len(names) == 0:
            return False
        name = names[0]
        if name in self.config.filter.blocklist:
            return True
        if name in self.config.filter.blocklist_standalone and name == action.strip():
            return True
        if name in self.config.filter.block_unless_regex and not re.search(
            self.config.filter.block_unless_regex[name], action
        ):
            return True
        return False

    # Parsing & multiline commands
    # -----------------------------

    def parse_submission_cmd_output(self, output: str) -> str | None:
        """Function for extracting diff patch submission at the end of an episode.

        Args:
            output: `submit` observation

        Returns:
            submission: diff patch submission or None if no submission was found
        """
        pattern = r"\<\<SUBMISSION\|\|(.*)\|\|SUBMISSION\>\>"
        match = re.search(pattern, output, re.DOTALL)
        if match is None:
            return None
        return match.group(1)

    def parse_actions(self, output: dict) -> tuple[str, str]:
        """Parse the model output into a thought and action."""
        return self.config.parse_function(output, self.config.commands)

    def guard_multiline_input(self, action: str) -> str:
        """Split action by multiline commands, then append the first line in each multiline command with "<< '{end_name}'".
        Multiline commands (which are specified by an end_name) are commands that span multiple lines and are terminated by a specific end_name.

        Their multi-line argument is sent using a heredoc, which is a way to send a multi-line string to a command in bash.
        """
        return _guard_multiline_input(action, self._get_first_multiline_cmd)

    def _get_first_multiline_cmd(self, action: str) -> re.Match | None:
        """Return the first match of a command pattern in the action string.
        Where first match is defined by the start of the match.

        The match object has three groups: (1) command name, (2) command arguments, (3) end name
        """
        patterns = {
            k: v
            for k, v in self._command_patterns.items()
            if k in self.config.multi_line_command_endings or k == self.config.submit_command
        }
        matches = list()
        for _, pat in patterns.items():
            match = pat.search(action)
            if match:
                matches.append(match)
        if len(matches) == 0:
            return None
        matches = sorted(matches, key=lambda x: x.start())
        return matches[0]

    def _get_command_patterns(self) -> dict[str, re.Pattern]:
        """Creates regular expressions for the commands"""

        _command_patterns = {}
        for command in self.config.commands:
            if command.end_name is not None:
                pat = re.compile(
                    rf"^\s*({command.name})\s*(.*?)^({command.end_name})\s*$",
                    re.DOTALL | re.MULTILINE,
                )
                _command_patterns[command.name] = pat
            else:
                pat = re.compile(rf"^\s*({command.name})\s*(.*?)$", re.MULTILINE)
                _command_patterns[command.name] = pat
        submit_pat = re.compile(
            rf"^\s*({self.config.submit_command})\s*(.*?)^({self.config.submit_command_end_name})\s*$",
            re.DOTALL | re.MULTILINE,
        )
        _command_patterns[self.config.submit_command] = submit_pat
        return _command_patterns
