from __future__ import annotations

import copy
import json
import re
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from simple_parsing.helpers.fields import field
from tenacity import RetryError

from sweagent import __version__, get_agent_commit_hash
from sweagent.agent.commands import Command, ParseCommand
from sweagent.agent.history_processors import HistoryProcessor
from sweagent.agent.hooks.abstract import AbstractAgentHook, CombinedAgentHook
from sweagent.agent.models import (
    APIStats,
    ContextWindowExceededError,
    CostLimitExceededError,
    ModelArguments,
    get_model,
)
from sweagent.agent.parsing import FormatError, ParseFunction

# from sweagent.agent.summarizer import SummarizerConfig
from sweagent.agent.utils import _guard_multiline_input
from sweagent.environment.config.problem_statement import ProblemStatement, ProblemStatementConfig
from sweagent.environment.swe_env import SWEEnv
from sweagent.types import AgentInfo, AgentRunResult, History, HistoryItem, Trajectory, TrajectoryStep
from sweagent.utils.config import _convert_paths_to_abspath
from sweagent.utils.log import get_logger


# todo: factor out tools config and potentially try to only give it to SWEEnv. Agent should only need allow-lists and the final tools documentation
class AgentConfig(BaseModel):
    system_template: str = ""
    instance_template: str = ""
    next_step_template: str = None  # type: ignore
    """Template for the next step. Defaults to instance_template."""

    next_step_no_output_template: str = None  # type: ignore
    """Template for the next step when the last output was empty. Defaults to next_step_template."""

    strategy_template: str | None = None
    demonstration_template: str | None = None
    # Paths to demonstrations. If path is not absolute, it is assumed to be
    # relative to the SWE_AGENT_CONFIG_ROOT (if set) or the SWE-agent repository root
    demonstrations: list[str] = field(default_factory=list)
    put_demos_in_history: bool = False  # if True, add demonstration to history instead of as a single message
    # defaults to format_error_template in ParseFunction
    format_error_template: str = None  # type: ignore
    # Paths to command files. If path is not absolute, it is assumed to be
    # relative to the SWE_AGENT_CONFIG_ROOT (if set) or the SWE-agent repository root
    command_files: list[str] = field(default_factory=list)
    env_variables: dict[str, Any] = field(default_factory=dict)
    util_functions: list[str] = field(default_factory=list)
    submit_command: str = "submit"
    parse_function: Any = "ThoughtActionParser"
    parse_command: Any = "ParseCommandBash"
    history_processor: Any = "DefaultHistoryProcessor"
    history_processor_args: dict[str, Any] = field(default_factory=dict)
    command_docs: str = None  # type: ignore
    # summarizer_config: SummarizerConfig = field(default_factory=SummarizerConfig)
    blocklist_error_template: str = "Interactive operation '{name}' is not supported by this environment"
    blocklist: tuple[str, ...] = (
        "vim",
        "vi",
        "emacs",
        "nano",
        "nohup",
        "git",
        "gdb",
    )
    blocklist_standalone: tuple[str, ...] = (
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
    )
    block_unless_regex: dict[str, str] = field(
        default_factory=lambda: {
            "radare2": r"\b(?:radare2)\b.*\s+-c\s+.*",
            "r2": r"\b(?:radare2)\b.*\s+-c\s+.*",
        }
    )
    # Should extract environment state in a json readable form
    state_command: Command = field(
        default_factory=lambda: Command(
            name="state",
            code="""state() {
            echo '{"working_dir": "'$(realpath --relative-to=$ROOT/.. $PWD)'"}';
        };""",
        )
    )
    # _subroutines: dict[str, Subroutine] = field(default_factory=dict)
    # subroutine_types: list[Subroutine] = field(default_factory=list)
    model: ModelArguments = field(default_factory=lambda: ModelArguments(name="gpt4"))
    multi_line_command_endings: dict[str, str] = field(default_factory=dict)
    submit_command_end_name: str | None = None

    @property
    def commands(self) -> list[Command]:
        _commands = []
        parse_command = ParseCommand.get(self.parse_command)
        for file in self.command_files:
            commands = parse_command.parse_command_file(file)
            util_functions = [command for command in commands if command.name.startswith("_")]
            commands = [command for command in commands if not command.name.startswith("_")]
            self.util_functions.extend(util_functions)
            _commands.extend(commands)
        return _commands

    def model_post_init(self, __context):
        self.command_files = _convert_paths_to_abspath(self.command_files)
        self.demonstrations = _convert_paths_to_abspath(self.demonstrations)

        if self.next_step_template is None:
            self.next_step_template = self.instance_template
        if self.next_step_no_output_template is None:
            self.next_step_no_output_template = self.next_step_template

        # object.__setattr__(self, "parse_command", ParseCommand.get(self.parse_command))
        parse_command = ParseCommand.get(self.parse_command)
        _commands = []
        for file in self.command_files:
            commands = parse_command.parse_command_file(file)

            util_functions = [command for command in commands if command.name.startswith("_")]
            commands = [command for command in commands if not command.name.startswith("_")]

            self.util_functions.extend(util_functions)
            _commands.extend(commands)

        multi_line_command_endings = {
            command.name: command.end_name
            # for command in [*self._commands, *self._subroutines.values()]
            for command in _commands
            if command.end_name is not None
        }
        self.multi_line_command_endings = multi_line_command_endings
        self.command_docs = parse_command.generate_command_docs(
            _commands,
            [],
            # self.subroutine_types,
            **self.env_variables,
        )
        # object.__setattr__(self, "parse_function", ParseFunction.get(self.parse_function))
        parse_function = ParseFunction.get(self.parse_function)
        if self.format_error_template is None:
            self.format_error_template = parse_function.format_error_template
        self.format_error_template = self.format_error_template.format(**self.__dict__)
        for command in _commands:
            if command.name == self.submit_command:
                self.submit_command_end_name = command.end_name
                break
        # object.__setattr__(
        #     self,
        #     "history_processor",
        #     HistoryProcessor.get(self.history_processor, **self.history_processor_args),
        # )
        # if "WINDOW" in self.env_variables:
        # window_size = self.env_variables["WINDOW"]
        # if self.summarizer_config.window_length < int(window_size):
        #     msg = f"Summarizer window length is set to {self.summarizer_config.window_length} which is less than the window length {window_size}"
        #     raise ValueError(msg)


# todo: separate out from_config. In particular separate out model (as a class, etc.)
# todo: Can this class be split up into separate responsibilities?
class Agent:
    """Agent handles the behaviour of the model and how it interacts with the environment."""

    def __init__(self, name: str, args: AgentConfig):
        self.name = name
        # todo: currently only used to get the model name, so might remove this later
        self._args = args
        # self.model = get_model(args.model, args.config._commands + args.config.subroutine_types)
        self.model = get_model(args.model, args.commands)
        # self.summarizer_model = get_model(
        #     args.summarizer_config.model if args.summarizer_config.model is not None else args.model
        # )
        self.config = args

        self.system_args = {
            "command_docs": self.config.command_docs,
            **self.config.env_variables,
        }
        self._parse_command_patterns()
        self.last_container_id = None
        self.logger = get_logger("agent", emoji="🤠")
        # Requires instance, so is set in `setup` methods
        self._rloop = None

        # Set in run method
        self._env: SWEEnv | None = None
        self._problem_statement: ProblemStatement | ProblemStatementConfig | None = None
        self.traj_path: Path | None = None

        #: Number of attempts to solve the issue when using a review loop
        self._i_attempt: int = 0

        #: The following three attributes collect the information about how the agent
        #: solved the problem.
        self._history_by_attempt: dict[int, list] = defaultdict(list)
        self._trajectory_by_attempt: dict[int, Trajectory] = defaultdict(list)
        self._info_by_attempt: dict[int, AgentInfo] = defaultdict(dict)  # type: ignore

        #: Variables to be referenced in the templates that are forwarded from one
        #: solution attempt to the next
        self._forwarded_vars: dict[str, Any] = {}

        self._history_processor = HistoryProcessor.get(
            self.config.history_processor, **self.config.history_processor_args
        )
        self._parse_function = ParseFunction.get(self.config.parse_function)

        self._chook = CombinedAgentHook()

    @property
    def history(self) -> History:
        """History that is passed on to the model.
        Use `_append_history` to modify.
        """
        return self._history_by_attempt[self._i_attempt]

    @history.setter
    def history(self, value: History):
        self._history_by_attempt[self._i_attempt] = value

    @property
    def trajectory(self) -> Trajectory:
        """Trajectory of the agent for the current instance. In contrast to `history`,
        this is mostly for the informational value of how the agent interacted with
        the environment and is also what is being used when replaying the trajectory
        """
        return self._trajectory_by_attempt[self._i_attempt]

    @trajectory.setter
    def trajectory(self, value: Trajectory):
        self._trajectory_by_attempt[self._i_attempt] = value

    @property
    def info(self) -> AgentInfo:
        """Information about the agent's run"""
        return self._info_by_attempt[self._i_attempt]

    @info.setter
    def info(self, value: AgentInfo):
        self._info_by_attempt[self._i_attempt] = value

    def add_hook(self, hook: AbstractAgentHook) -> None:
        """Add hook to agent"""
        hook.on_init(agent=self)
        self._chook.add_hook(hook)

    def _append_history(self, item: HistoryItem) -> None:
        """Adds an item to the history."""
        self._chook.on_query_message_added(**item)
        self.history.append(item)

    # todo: klieret: Long term: Might make more sense to reinitialize the agent class for every instance instead of this
    def setup(self, init_model_stats: APIStats | None = None) -> None:
        """Setup the agent for a new instance. This includes
        formatting the system message and adding demonstrations to the history.

        Args:
            instance_args: Arguments for the instance
        """

        self._i_attempt = 0
        self._history_by_attempt = defaultdict(list)
        self._trajectory_by_attempt = defaultdict(list)
        self._info_by_attempt = defaultdict(dict)  # type: ignore
        self._forwarded_vars = {}
        if self._rloop is not None:
            self._forwarded_vars = self._rloop.get_forwarded_vars()

        self.setup_attempt(init_model_stats=init_model_stats)

        self._chook.on_setup_done()

    def setup_attempt(self, *, init_model_stats: APIStats | None = None) -> None:
        """Setup the agent for a new attempt. This includes resetting the model stats."""

        if self._i_attempt > 0 and init_model_stats is not None:
            msg = (
                "We might be dealing with nested retries, where subroutines are mixed with retries. "
                "Currently, this messes up accounting with init_model_stats."
            )
            raise ValueError(msg)
        if self._i_attempt > 0:
            assert self._env is not None  # mypy
            self._env.reset_for_new_attempt()
        self.model.reset_stats(init_model_stats)
        # self.model = get_model(self._args.model, self.config._commands + self.config.subroutine_types)
        # fixme: This doesn't reset total cost
        assert self._problem_statement is not None
        system_msg = self.config.system_template.format(
            **self.system_args, problem_statement=self._problem_statement.get_problem_statement()
        )
        self.logger.info(f"SYSTEM ({self.name})\n{system_msg}")
        self._append_history(HistoryItem({"role": "system", "content": system_msg, "agent": self.name}))
        # todo: This should be moved somewhere
        if "history_to_messages" in dir(self.model):
            for demonstration_path in self.config.demonstrations:
                if self.config.demonstration_template is None and not self.config.put_demos_in_history:
                    msg = "Cannot use demonstrations without a demonstration template or put_demos_in_history=True"
                    raise ValueError(msg)

                # Load history
                self.logger.info(f"DEMONSTRATION: {demonstration_path}")
                demo_history = json.loads(Path(demonstration_path).read_text())["history"]
                demo_history = [
                    entry
                    for entry in demo_history
                    if ("agent" not in entry) or ("agent" in entry and entry["agent"] == self.name)
                ]

                if self.config.put_demos_in_history:
                    if self.config.demonstration_template is not None:
                        self.logger.warning("Demonstration template is ignored for put_demos_in_history=True")
                    # Add demonstration to history directly as separate messages
                    for entry in demo_history:
                        if entry["role"] != "system":
                            entry["is_demo"] = True
                            self._append_history(entry)
                else:
                    # Add demonstration as single message to history
                    demo_message = self.model.history_to_messages(
                        demo_history,
                        is_demonstration=True,
                    )
                    assert self.config.demonstration_template is not None
                    demonstration = self.config.demonstration_template.format(demonstration=demo_message)
                    self._append_history(
                        {
                            "agent": self.name,
                            "content": demonstration,
                            "is_demo": True,
                            "role": "user",
                        },
                    )

    # todo: turn into method
    @property
    def local_history(self) -> list[dict[str, str]]:
        """Return the history of the agent since the last reset."""
        return self._history_processor([entry for entry in self.history if entry["agent"] == self.name])

    def _get_total_stats(self) -> APIStats:
        """Combine model stats of different attempts"""
        total_stats = APIStats()
        for stats in self._info_by_attempt.values():
            assert "model_stats" in stats  # mypy
            attempt_stats = APIStats(**stats["model_stats"])  # type: ignore
            total_stats += attempt_stats
        if self._rloop is not None:
            total_stats += self._rloop.model_stats
        return total_stats

    def save_trajectory(
        self,
    ) -> None:
        """Save the trajectory to disk.
        This includes the history, the environment state, and the model stats.
        """

        def get_attempt_data(attempt_idx: int) -> dict[str, Any]:
            """Get data saved for every attempt"""
            assert self._env is not None
            # The deepcopy here is important because else the
            # data["info"]["model_stats"] update will create havoc!
            return copy.deepcopy(
                {
                    "environment": self._env.name,
                    "trajectory": self._trajectory_by_attempt[attempt_idx],
                    "history": self._history_by_attempt[attempt_idx],
                    "info": self._info_by_attempt[attempt_idx],
                }
            )

        data = {
            **get_attempt_data(0),
        }

        assert self.traj_path is not None
        self.traj_path.write_text(json.dumps(data, indent=2))

    def _get_first_multiline_cmd(self, action: str) -> re.Match | None:
        """Return the first match of a command pattern in the action string.
        Where first match is defined by the start of the match.

        The match object has three groups: (1) command name, (2) command arguments, (3) end name
        """
        patterns = {
            k: v
            for k, v in self.command_patterns.items()
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

    def _guard_multiline_input(self, action: str) -> str:
        """Split action by multiline commands, then append the first line in each multiline command with "<< '{end_name}'".
        Multiline commands (which are specified by an end_name) are commands that span multiple lines and are terminated by a specific end_name.

        Their multi-line argument is sent using a heredoc, which is a way to send a multi-line string to a command in bash.
        """
        return _guard_multiline_input(action, self._get_first_multiline_cmd)

    def _parse_command_patterns(self) -> None:
        """Sets self.command_patterns and self.subroutine_patterns"""

        self.command_patterns = dict()
        for command in self.config.commands:
            if command.end_name is not None:
                pat = re.compile(
                    rf"^\s*({command.name})\s*(.*?)^({command.end_name})\s*$",
                    re.DOTALL | re.MULTILINE,
                )
                self.command_patterns[command.name] = pat
            else:
                pat = re.compile(rf"^\s*({command.name})\s*(.*?)$", re.MULTILINE)
                self.command_patterns[command.name] = pat
        if hasattr(self.config, "submit_command_end_name"):
            submit_pat = re.compile(
                rf"^\s*({self.config.submit_command})\s*(.*?)^({self.config.submit_command_end_name})\s*$",
                re.DOTALL | re.MULTILINE,
            )
        else:
            submit_pat = re.compile(rf"^\s*({self.config.submit_command})(\s*)$", re.MULTILINE)  # group 2 is nothing
        self.command_patterns[self.config.submit_command] = submit_pat

    def forward(self, observation: str, available_actions: list[str], state: dict[str, str]) -> tuple[str, str, str]:
        """Forwards the model, i.e., queries the model with the current trajectory and observation.
        This is identical to `self.forward_with_error_check`, but adds the output to the trajectory.

        Args:
            observation: Observation
            available_actions: Currently not used
            state:

        Returns:
            thought: model reasoning
            action: action that the model proposes
            output: raw model output (not output of the action)
        """
        thought, action, output = self.forward_with_error_check(observation, state)

        self._append_history(
            {
                "role": "assistant",
                "content": output,
                "thought": thought,
                "action": action,
                "agent": self.name,
            },
        )

        self.logger.info(f"💭 THOUGHT ({self.name})\n{thought}")
        self.logger.info(f"🎬 ACTION ({self.name})\n{action}")

        return thought, action, output

    def forward_model(self, observation: str, state: dict[str, str]) -> str:
        """Query the model with the current state and observation with the appropriate template.
        In most cases you want to use `self.forward_with_error_check` instead to handle requeueing etc.

        Returns:
            output: raw model output (not output of the command)
        """
        templates: list[str] = []
        # Determine observation template based on what prior observation was
        if self.history[-1]["role"] == "system" or self.history[-1].get("is_demo", False):
            # Show instance template if prev. obs. was initial system message
            templates = [self.config.instance_template]
            if self.config.strategy_template is not None:
                templates.append(self.config.strategy_template)
        elif observation is None or observation.strip() == "":
            # Show no output template if observation content was empty
            templates = [self.config.next_step_no_output_template]
        else:
            # Show standard output template if there is observation content
            templates = [self.config.next_step_template]

        # Populate selected template(s) with information (e.g., issue, arguments, state)
        messages = []
        assert self._problem_statement is not None
        for template in templates:
            messages.append(
                template.format(
                    **self.system_args,
                    **state,
                    observation=observation or "",
                    **self._forwarded_vars,
                    problem_statement=self._problem_statement.get_problem_statement(),
                ),
            )

        message = "\n".join(messages)

        self.logger.info(f"🤖 MODEL INPUT\n{message}")
        self._append_history({"role": "user", "content": message, "agent": self.name})

        self._chook.on_model_query(messages=self.local_history, agent=self.name)
        return self.model.query(self.local_history)

    def retry_after_format_fail(self, output: str) -> str:
        """Ask the model to correct (without committing to persistent history) after a malformatted model output"""
        format_error_template = self.config.format_error_template

        self.logger.warning(f"MALFORMED OUTPUT\n{output}")
        self.logger.warning(f"FORMAT ERROR\n{format_error_template}")

        temp_history = self.local_history + [
            {"role": "assistant", "content": output, "agent": self.name},
            {"role": "user", "content": format_error_template, "agent": self.name},
        ]
        return self.model.query(temp_history)

    def retry_after_blocklist_fail(self, output: str, action: str) -> str:
        """Ask the model to correct (without committing to persistent history) after a disallowed command"""
        name = action.strip().split()[0]
        blocklist_error_message = self.config.blocklist_error_template.format(name=name)

        self.logger.warning(f"BLOCKLISTED OUTPUT\n{output}")
        self.logger.warning(f"BLOCKLIST ERROR\n{blocklist_error_message}")

        temp_history = self.local_history + [
            {"role": "assistant", "content": output, "agent": self.name},
            {"role": "user", "content": blocklist_error_message, "agent": self.name},
        ]
        return self.model.query(temp_history)

    def should_block_action(self, action: str) -> bool:
        """Check if the command should be blocked."""
        names = action.strip().split()
        if len(names) == 0:
            return False
        name = names[0]
        if name in self.config.blocklist:
            return True
        if name in self.config.blocklist_standalone and name == action.strip():
            return True
        if name in self.config.block_unless_regex and not re.search(self.config.block_unless_regex[name], action):
            return True
        return False

    def check_format_and_requery(
        self,
        output: str,
    ) -> tuple[str, str, str]:
        """Checks model output. If the output is malformatted or the action is blocked, call
        `self.retry_after_format_fail` or `self.retry_after_blocklist_fail`.

        Try to parse the output into a thought and action. Retry if the output is malformatted or the action is blocked.

        Returns:
            thought: model reasoning
            action: action that the model proposes
            output: raw model output
        """
        # Condition for handling outputs with no thought (just action)
        if self.model.args.name == "human":
            return "", output, output
        elif self.model.args.name == "human_thought":
            thought, action = ParseFunction.get("ThoughtActionParser")(
                output,
                self.config.commands,
                strict=False,
            )
            return thought, action, output

        format_fails = blocklist_fails = 0

        while format_fails + blocklist_fails <= 2:
            try:
                thought, action = self._parse_function(
                    output,
                    self.config.commands,
                    strict=False,
                )
            except KeyboardInterrupt:
                raise
            except FormatError:
                format_fails += 1
                output = self.retry_after_format_fail(output)
                continue
            if self.should_block_action(action):
                blocklist_fails += 1
                output = self.retry_after_blocklist_fail(output, action)
            else:
                return thought, action, output
        self.logger.warning(f"Malformat limit reached: \n{output}")
        return "Exit due to format error", "exit_format", output

    def forward_with_error_check(self, observation: str, state: dict[str, str]) -> tuple[str, str, str]:
        """Wrapper around `self.forward_model` that handles errors and retries
        due to format errors or blocked actions.

        Returns:
            thought: model reasoning
            action: action that the model proposes
            output: raw model output
        """
        try:
            return self.check_format_and_requery(self.forward_model(observation, state))
        except KeyboardInterrupt:
            raise
        except RuntimeError as e:
            self.logger.warning(f"Runtime error: {e}")
            return (
                f"Exit due to runtime error: {e}",
                "exit_error",
                f"exit due to runtime error: {e}",
            )
        except ContextWindowExceededError:
            self.logger.warning("Context window exceeded")
            return "Exit due to context window", "exit_context", "Exit due to context window"
        except CostLimitExceededError:
            self.logger.warning("Cost limit exceeded")
            return "Exit due to cost limit", "exit_cost", "Exit due to cost limit"
        except RetryError as e:
            self.logger.warning(f"Retry error: {e}")
            return (
                f"Exit due to retry error: {e}",
                "exit_api",
                f"exit due to retry error: {e}",
            )

    def init_environment_vars(self):
        self.set_environment_vars(self.config.env_variables)

    def set_environment_vars(self, env_variables: dict[str, Any]) -> None:
        """Sets environment variables in the container and for example makes sure
        that all the commands are available in the PATH on the container.
        """

        commands_to_execute = (
            [self.config.state_command.code]
            +
            # [code for code in self.config.util_functions] +
            # [command.code for command in self.config._commands] +
            [f"{k}={v}" for k, v in env_variables.items()]
        )
        commands = "\n".join(commands_to_execute)
        assert self._env is not None
        try:
            self._env.communicate(commands, require_zero=True)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.logger.warning(f"Failed to set environment variables: {traceback.format_exc()}")
            raise e
        command_files = list()
        for file in self.config.command_files:
            datum = dict()
            with open(file) as f:
                contents = f.read()
            datum["contents"] = contents
            filename = Path(file).name
            if not contents.strip().startswith("#!"):
                if filename.endswith(".sh"):
                    # files are sourced, so they are not executable
                    datum["name"] = Path(file).name
                    datum["type"] = "source_file"
                elif filename.startswith("_"):
                    # files are sourced, so they are not executable
                    datum["name"] = Path(file).name
                    datum["type"] = "utility"
                else:
                    msg = (
                        f"Non-shell script file {file} does not start with shebang.\n"
                        "Either add a shebang (#!) or change the file extension to .sh if you want to source it.\n"
                        "You can override this behavior by adding an underscore to the file name (e.g. _utils.py)."
                    )
                    raise ValueError(msg)
            else:
                # scripts are made executable
                datum["name"] = Path(file).name.rsplit(".", 1)[0]
                datum["type"] = "script"
            command_files.append(datum)
        self._env.add_commands(command_files)

    def get_state(self) -> dict[str, str]:
        """If a state command is defined, execute it in the environment and return the result as a dictionary."""
        if not self.config.state_command:
            return {}
        assert self._env is not None
        state = self._env.communicate(self.config.state_command.name)
        try:
            return json.loads(state)
        except json.JSONDecodeError as e:
            msg = f"State {state!r} is not valid json. This is an internal error, please report it."
            raise ValueError(msg) from e

    def step(self, observation: str) -> tuple[str, bool]:
        """Run a step of the agent: Take the last observation, combine it with all other context
        (i.e., the history of thoughts and actions), then execute the action and return the new observation.
        Also saves the new trajectory.

        Returns:
            observation: Observation
            done: Whether `submit` or another exit reason was called
        """

        assert self._env is not None

        self._chook.on_step_start()

        # fixme: This will probably fail if the state command is not set
        # todo: parse state here rather than in forward
        state = self.get_state()
        thought, raw_action, output = self.forward(observation, self._env.get_available_actions(), state)
        self._chook.on_actions_generated(thought=thought, action=raw_action, output=output)
        run_action: str = self._guard_multiline_input(raw_action)

        # Loop over sub-actions (if any)
        execution_t0 = time.perf_counter()
        self._chook.on_action_started(action=run_action)
        observation, _, done, _info = self._env.step(run_action)
        self.info.update(_info)
        self._chook.on_action_executed(obs=observation, done=done)
        execution_time = time.perf_counter() - execution_t0

        trajectory_step = TrajectoryStep(
            {
                "action": raw_action,
                "observation": observation,
                "response": output,
                "state": state,
                "thought": thought,
                "execution_time": execution_time,
            },
        )
        self.trajectory.append(trajectory_step)
        model_stats: APIStats = self.model.stats
        self.info["model_stats"] = model_stats.to_dict()
        self._chook.on_step_done(trajectory_step=trajectory_step, model_stats=model_stats)
        return observation, done

    # todo: Set env already in  setup?
    def run(
        self,
        problem_statement: ProblemStatement | ProblemStatementConfig,
        env: SWEEnv,
        observation: str = "",
        traj_dir: Path = Path("."),
        init_model_stats: APIStats | None = None,
    ) -> AgentRunResult:
        """Run the agent on a problem instance. This method contains the
        main loop that repeatedly calls `self._step` until the problem is solved.

        Args:
            setup_args: Arguments to pass to the agent's setup method.
            env: The environment to run the agent on.
            observation: Output from environment setup
            traj_dir: Directory to save the trajectory to
            init_model_stats: Initial model stats to use for the run.
        """
        self._problem_statement = problem_statement
        self._env = env
        # todo: Shouldn't this be moved to setup?
        self.init_environment_vars()
        self.setup(init_model_stats)

        # Save/reset some attributes
        self.trajectory = Trajectory()
        self.info = AgentInfo()
        self.info["swe_agent_hash"] = get_agent_commit_hash()
        self.info["swe_agent_version"] = __version__
        self.traj_path = traj_dir / (self._problem_statement.id + ".traj")

        self.logger.info("Trajectory will be saved to %s", self.traj_path)

        # Run action/observation loop
        self._chook.on_run_start()
        done = False
        while not done:
            observation, done = self.step(observation)
            self.save_trajectory()
        self._chook.on_run_done(trajectory=self.trajectory, info=self.info)

        self.logger.info("Trajectory saved to %s", self.traj_path)

        return AgentRunResult(info=self.info, trajectory=self.trajectory)
