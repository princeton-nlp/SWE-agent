import asyncio
import json
import re
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, Field
from swerex.runtime.abstract import AbstractRuntime, BashAction, WriteFileRequest
from swerex.runtime.abstract import Command as RexCommand

from sweagent.tools.commands import Command, ParseCommand, ParseCommandBash
from sweagent.tools.parsing import ParseFunction, ThoughtActionParser
from sweagent.tools.utils import _guard_multiline_input
from sweagent.utils.config import _convert_paths_to_abspath
from sweagent.utils.log import get_logger


class ToolFilterConfig(BaseModel):
    blocklist_error_template: str = "Interactive operation '{name}' is not supported by this environment"
    blocklist: list[str] = [
        "vim",
        "vi",
        "emacs",
        "nano",
        "nohup",
        "git",
        "gdb",
    ]
    blocklist_standalone: list[str] = [
        "python",
        "python3",
        "ipython",
        "bash",
        "sh",
        "exit",
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
    command_files: list[Path] = []

    env_variables: dict[str, Any] = {}
    """Shorthand to set environment variables for the tools, effectively
    equivalent to adding `export VARNAME=value` to the `reset_commands`.
    """

    submit_command: str = "submit"

    parse_function: ParseFunction = Field(default_factory=ThoughtActionParser)
    parse_command: ParseCommand = Field(default_factory=ParseCommandBash)

    format_error_template: str = None  # type: ignore
    """Defaults to format_error_template in ParseFunction"""

    command_docs: str = None  # type: ignore
    multi_line_command_endings: dict[str, str] = {}
    submit_command_end_name: str | None = None

    install_commands: list[str] = [
        "mkdir -p /root/commands",
        "touch /root/commands/__init__.py",
        "export PATH=$PATH:/root/commands",
    ]
    """Commands to install dependencies and tools.
    These commands are executed in a subprocess and are not part of the environment state.
    """

    reset_commands: list[str | list[str]] = []
    """Commands to reset the environment. They will also be called when we start the environment.
    Unlike `install_commands`, these commands are part of the environment state.
    """

    state_command: Command = Command(
        name="state",
        code="""state() {
            echo '{"working_dir": "'$(realpath --relative-to=$ROOT/.. $PWD)'"}';
        };""",
    )
    """Should extract environment state in a json readable form"""

    # todo: move to ToolHandler?
    @property
    def commands(self) -> list[Command]:
        """Read command files and returned parsed command objects"""
        commands = []
        for file in self.command_files:
            parsed_commands = self.parse_command.parse_command_file(file)
            commands.extend([command for command in parsed_commands if not command.name.startswith("_")])
        return commands

    # todo: can some of these be moved to ToolHandler?
    def model_post_init(self, __context):
        self.command_files = _convert_paths_to_abspath(self.command_files)

        # for caching:
        commands = self.commands

        multi_line_command_endings = {
            command.name: command.end_name for command in commands if command.end_name is not None
        }
        self.multi_line_command_endings = multi_line_command_endings
        self.command_docs = self.parse_command.generate_command_docs(
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


# todo: Take runtime in methods, not in constructor, so I can pass it to the agent
class ToolHandler:
    def __init__(self, tools: ToolConfig, runtime: AbstractRuntime):
        """This class handles most of the tool usage. It has the following responsibilities:

        - Install the tools
        - Parse commands and handle multiline commands
        - Decide if an action should be blocked
        - Get the current state of the environment
        """
        self.config = tools
        self._runtime = runtime
        # partially initialized in `install_commands`.
        self._reset_commands = []
        self._command_patterns = self._get_command_patterns()
        self.logger = get_logger("Tools", emoji="🔧")

    @classmethod
    def from_config(cls, config: ToolConfig, runtime: AbstractRuntime) -> Self:
        return cls(config, runtime)

    def install(self) -> None:
        self._install_commands()
        self._make_state_command_available()
        self.reset()

    def _install_commands(self) -> None:
        """Make sure all commands are available in the container"""
        for file in self.config.command_files:
            contents = file.read_text()
            source = False
            mark_executable = False
            if not contents.strip().startswith("#!"):
                if file.suffix == ".sh":
                    name = file.name
                    source = True
                elif file.name.startswith("_"):
                    name = file.name
                else:
                    msg = (
                        f"Non-shell script file {file} does not start with shebang.\n"
                        "Either add a shebang (#!) or change the file extension to .sh if you want to source it.\n"
                        "You can override this behavior by adding an underscore to the file name (e.g. _utils.py)."
                    )
                    raise ValueError(msg)
            else:
                name = file.name.rpartition(".")[0]
                mark_executable = True

            self.logger.debug(f"Installing command {name} ({source=}, {mark_executable=})")
            asyncio.run(self._runtime.write_file(WriteFileRequest(content=contents, path=f"/root/commands/{name}")))
            if source:
                self._reset_commands.append(f"source /root/commands/{name}")
            if mark_executable:
                asyncio.run(
                    self._runtime.execute(RexCommand(command=f"chmod +x /root/commands/{name}", shell=True, check=True))
                )
        for command in self.config.install_commands:
            asyncio.run(self._runtime.run_in_session(BashAction(command=command, timeout=1, check=True)))

    def _make_state_command_available(self) -> None:
        asyncio.run(
            self._runtime.run_in_session(BashAction(command=self.config.state_command.code, timeout=1, check=True))
        )

    def _set_env_variables(self) -> None:
        _env_setters = [f"export {k}={v}" for k, v in self.config.env_variables.items()]
        command = " && ".join(_env_setters)
        asyncio.run(
            self._runtime.run_in_session(
                BashAction(command=command, timeout=1, check=True, error_msg="Failed to set environment variables")
            )
        )

    def reset(self) -> None:
        self.logger.info("Resetting tools")
        self._set_env_variables()
        asyncio.run(
            self._runtime.run_in_session(BashAction(command=" && ".join(self._reset_commands), timeout=1, check=True))
        )

    def get_state(self) -> dict[str, str]:
        """If a state command is defined, execute it in the environment parse it as json and return the result.
        This can be used to extract environment variables etc. from the environment.
        """
        if not self.config.state_command:
            return {}
        state = asyncio.run(
            self._runtime.run_in_session(BashAction(command=self.config.state_command.name, check=True))
        )
        output = state.output.strip()
        if not output:
            return {}
        try:
            state = json.loads(output)
        except json.JSONDecodeError as e:
            msg = f"State {output!r} is not valid json. This is an internal error, please report it."
            raise ValueError(msg) from e
        self.logger.debug(f"Retrieved state from environment: {state}")
        return state

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

    def guard_multiline_input(self, action: str) -> str:
        """Split action by multiline commands, then append the first line in each multiline command with "<< '{end_name}'".
        Multiline commands (which are specified by an end_name) are commands that span multiple lines and are terminated by a specific end_name.

        Their multi-line argument is sent using a heredoc, which is a way to send a multi-line string to a command in bash.
        """
        return _guard_multiline_input(action, self._get_first_multiline_cmd)

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

    def parse_submission_cmd_output(self, output: str) -> str | None:
        """Function for extracting diff patch submission at the end of an episode.

        Args:
            output: `submit` observation

        Returns:
            submission: diff patch submission
        """
        pattern = r"\<\<SUBMISSION\|\|(.*)\|\|SUBMISSION\>\>"
        match = re.search(pattern, output, re.DOTALL)
        if match is None:
            return None
        return match.group(1)

    def parse_actions(self, output: str) -> tuple[str, str]:
        """Parse the model output into a thought and action."""
        return self.config.parse_function(output, self.config.commands)
