from __future__ import annotations

import json
import re
from dataclasses import dataclass
from operator import itemgetter
from pathlib import Path
from typing import Any, TypedDict

from simple_parsing.helpers.fields import field
from simple_parsing.helpers.flatten import FlattenedAccess
from simple_parsing.helpers.serialization.serializable import FrozenSerializable
from tenacity import RetryError

from sweagent.agent.commands import Command, ParseCommand
from sweagent.agent.history_processors import HistoryProcessor
from sweagent.agent.manual_input import ManualInput
from sweagent.agent.models import (
    APIStats,
    ContextWindowExceededError,
    CostLimitExceededError,
    ModelArguments,
    ModelQueryResult,
    get_last_valid_tool_use_name,
    get_model,
    make_model_query_result,
    make_assistant_content,
    make_user_reply_content,
)
from sweagent.agent.parsing import FormatError, ParseFunction
from sweagent.environment.swe_env import SWEEnv
from sweagent.utils.config import convert_path_to_abspath, convert_paths_to_abspath
from sweagent.utils.log import get_logger
from sweagent.utils.instrumentation import instrument

logger = get_logger("agents")

@dataclass(frozen=True)
class Subroutine(FrozenSerializable):
    name: str
    agent_file: str
    # one of "action", "observation", "response", "state", "thought"
    return_type: str = None  # type: ignore
    init_observation: str | None = None
    end_name: str | None = None
    signature: str | None = None
    docstring: str | None = None
    model: ModelArguments | None = None
    agent_args: Any | None = None


@dataclass(frozen=True)
class AgentConfig(FrozenSerializable):
    system_template: str
    instance_template: str
    next_step_template: str | None = None  # defaults to instance_template
    next_step_no_output_template: str | None = None  # defaults to next_step_template
    strategy_template: str | None = None
    demonstration_template: str | None = None
    # Paths to demonstrations. If path is not absolute, it is assumed to be
    # relative to the SWE_AGENT_CONFIG_ROOT (if set) or the SWE-agent repository root
    demonstrations: list[str | Path] = field(default_factory=list)
    put_demos_in_history: bool = False  # if True, add demonstration to history instead of as a single message
    # defaults to format_error_template in ParseFunction
    format_error_template: str = None  # type: ignore
    # Paths to command files. If path is not absolute, it is assumed to be
    # relative to the SWE_AGENT_CONFIG_ROOT (if set) or the SWE-agent repository root
    command_files: list[str | Path] = field(default_factory=list)
    env_variables: dict[str, str] = field(default_factory=dict)
    util_functions: list[str] = field(default_factory=list)
    submit_command: str = "submit"
    parse_function: str = "ThoughtActionParser"
    parse_command: str = "ParseCommandBash"
    history_processor: str = "DefaultHistoryProcessor"
    history_processor_args: dict[str, Any] = field(default_factory=dict)
    command_docs: str = None  # type: ignore
    blocklist_error_template: str = "Interactive operation '{name}' is not supported by this environment"
    blocklist: tuple[str, ...] = (
        "vim",
        "vi",
        "emacs",
        "nano",
        "nohup",
        "git",
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
    )
    # Should extract environment state in a json readable form
    state_command: Command = Command(
        name="state",
        code="""state() {
            echo '{"working_dir": "'$(realpath --relative-to=$ROOT/.. $PWD)'"}';
        };""",
    )
    _commands: list[Command] = field(default_factory=list)
    _subroutines: dict[str, Subroutine] = field(default_factory=dict)
    subroutine_types: list[Subroutine] = field(default_factory=list)
    tdd: bool = False

    def init_with_args(self, tdd: bool):
        if tdd:
            # Add tdd commands before they are processed below.
            self.command_files.append("config/commands/_tdd.sh")

        object.__setattr__(self, "command_files", convert_paths_to_abspath(self.command_files))
        object.__setattr__(self, "demonstrations", convert_paths_to_abspath(self.demonstrations))

        if self.next_step_template is None:
            object.__setattr__(self, "next_step_template", self.instance_template)
        if self.next_step_no_output_template is None:
            object.__setattr__(self, "next_step_no_output_template", self.next_step_template)

        object.__setattr__(self, "parse_command", ParseCommand.get(self.parse_command))
        for file in self.command_files:
            try:
                commands = self.parse_command.parse_command_file(file)
            except Exception as err:
                raise ValueError(f"Failed to parse commands from {file}: {err}")

            util_functions = [command for command in commands if command.name.startswith("_")]
            commands = [command for command in commands if not command.name.startswith("_")]

            object.__setattr__(self, "util_functions", self.util_functions + util_functions)
            object.__setattr__(self, "_commands", self._commands + commands)

        for subroutine in self.subroutine_types:
            if subroutine.name == "submit":
                msg = "Cannot use 'submit' as a subroutine name"
                raise ValueError(msg)
            agent_args = AgentArguments(
                model=subroutine.model,
                config_file=subroutine.agent_file,
            )
            object.__setattr__(subroutine, "agent_args", agent_args)
            object.__setattr__(self, "_subroutines", {**self._subroutines, subroutine.name: subroutine})

        multi_line_command_endings = {
            command.name: command.end_name
            for command in [*self._commands, *self._subroutines.values()]
            if command.end_name is not None
        }
        object.__setattr__(self, "multi_line_command_endings", multi_line_command_endings)
        object.__setattr__(
            self,
            "command_docs",
            self.parse_command.generate_command_docs(
                self._commands,
                self.subroutine_types,
                **self.env_variables,
            ),
        )
        object.__setattr__(self, "parse_function", ParseFunction.get(self.parse_function))
        if self.format_error_template is None:
            object.__setattr__(
                self,
                "format_error_template",
                self.parse_function.format_error_template,
            )
        object.__setattr__(
            self,
            "format_error_template",
            self.format_error_template.format(**self.__dict__),
        )
        for command in self._commands:
            if command.name == self.submit_command:
                object.__setattr__(self, "submit_command_end_name", command.end_name)
                break
        object.__setattr__(
            self,
            "history_processor",
            HistoryProcessor.get(self.history_processor, **self.history_processor_args),
        )


@dataclass(frozen=True)
class AgentArguments(FlattenedAccess, FrozenSerializable):
    """Configure the agent's behaviour (templates, parse functions, blocklists, ...)."""
    model: ModelArguments = None

    # Policy can only be set via config yaml file from command line
    config_file: Path | None = None
    config: AgentConfig | None = field(default=None, cmd=False)

    # We put tdd on the agent args because it needs it in post_init.
    tdd: bool = False

    manual_input_conversation_path: Path | None = None
    manual_input_continuation_label: str | None = None

    def __post_init__(self):
        if self.config is None and self.config_file is not None:
            # If unassigned, we load the config from the file to store its contents with the overall arguments
            logger.debug(f"Loading config from '{self.config_file}'...")
            try:
                config = AgentConfig.load_yaml(self.config_file)

                # NOTE: We need to explicitely patch things through because of carelessly designed initialization logic.
                #       → Complex initialization logic should generally make it easy to provide external inputs, e.g. via DI.
                config.init_with_args(self.tdd)
            except Exception as err:
                # stack = ''.join(traceback.format_exception(type(err), err, err.__traceback__))
                raise ValueError(f"Failed to load config from {self.config_file}: {err}")
            object.__setattr__(self, "config", config)
        assert self.config is not None  # mypy
        for subroutine in getattr(self.config, "subroutines", {}).values():
            model_args = subroutine.model
            object.__setattr__(
                model_args,
                "per_instance_cost_limit",
                self.model.per_instance_cost_limit,
            )
            object.__setattr__(model_args, "total_cost_limit", self.model.total_cost_limit)


class TrajectoryStep(TypedDict):
    action: str
    observation: str
    response: ModelQueryResult
    state: str | None
    thought: str


class AgentHook:
    def on_init(self): ...

    def on_run_start(
        self,
    ): ...

    def on_step_start(self): ...

    def on_actions_generated(self, *, thought: str, action: str, output: ModelQueryResult): ...

    def on_sub_action_started(self, *, sub_action: str): ...

    def on_sub_action_executed(self, *, obs: str, done: bool): ...

    def on_step_done(self, *, trajectory_step: TrajectoryStep, model_stats: APIStats): ...

    def on_run_done(self): ...

    def on_model_query(self, *, query: str, agent: str):
        """Actually query the model with the complete history."""

    def on_query_message_added(
        self,
        *,
        role: str,
        content: str,
        agent: str,
        is_demo: bool = False,
        thought: str = "",
        action: str = "",
    ): ...


class Agent:
    """Agent handles the behaviour of the model and how it interacts with the environment."""

    def __init__(self, name: str, args: AgentArguments, env: SWEEnv):
        self.name = name

        # We added `env` as a class property because its the main interface for the agent and a constant throughout the agent's lifecycle.
        self.env = env

        self.model = get_model(args.model, args.config._commands + args.config.subroutine_types)
        self.config = args.config
        self.made_initial_prompt = False
        assert self.config is not None  # mypy
        self.system_args = {
            "command_docs": self.config.command_docs,
            **self.config.env_variables,
        }
        self.instance_args = None
        self._parse_command_patterns()
        self.history = []
        self.last_container_id = None
        self.hooks = []
        self.logger = get_logger(f"Agent[{name}]")
        self.manual_input = ManualInput(args.manual_input_conversation_path, args.manual_input_continuation_label)
        self.initial_model_response = None

    def add_hook(self, hook: AgentHook):
        """Add hook to agent"""
        hook.on_init()
        self.hooks.append(hook)

    def _assert_tdd_history_entries(self, history=None):
        if self.env.tdd:
            # count tdd entries
            history = history or self.history
            tdd_count = sum(1 for entry in history if entry.get("tdd"))
            if tdd_count != 1:
                raise ValueError(
                    f"There should always be exactly 1 TDD entry in history, but found {tdd_count} (using history_processor='{self.config.history_processor}'): {repr(history)}"
                )

    def _append_history(self, item: dict):
        for hook in self.hooks:
            hook.on_query_message_added(**item)
        self.history.append(item)

    # ###########################################################################
    # TDD stuff.
    # ###########################################################################

    def _system_repro_prompt(self):
        # Read repro instructions.
        repro_fpath = convert_path_to_abspath(
            "config/_tdd_repro_prompt.md" if self.env.tdd else "config/_not_tdd_repro_prompt.md",
        )
        return Path(repro_fpath).read_text("utf-8")

    # Unflag all tdd entries from history, so it can be compressed.
    def _unflag_tdd_history(self):
        # self._assert_tdd_history_entries()

        for entry in self.history:
            if "tdd" in entry:
                entry["tdd"] = False

    # ###########################################################################
    # setup and more
    # ###########################################################################

    def setup(self, env: SWEEnv, instance_args, init_model_stats=None) -> None:
        """Setup the agent for a new instance. This includes
        formatting the system message and adding demonstrations to the history.

        Args:
            instance_args: Arguments for the instance
        """
        assert self.config is not None  # mypy
        self.model.setup(init_model_stats)
        self.instance_args = instance_args

        if self.manual_input.enabled():
            history_and_patch = self.manual_input.load_conversation()
            if history_and_patch is not None:
                history, patch = history_and_patch
                self.initial_model_response = history[-1]
                assert self.initial_model_response["role"] == "assistant"
                assert self.initial_model_response["action"] == "tdd_repro"
                self.history = history[:-1]
                self.made_initial_prompt = True
                if patch is not None:
                    env.apply_conversation_patch(patch)

                continuation = self.manual_input.load_continuation_file()

                if continuation is not None:
                    self.logger.info(f"Continuing from manual input:\n{continuation}")
                    continuation_file_path = "/root/continuation.md"
                    env.copy_string_to_container_file(continuation, continuation_file_path)
                    env.communicate_with_handling(f'export MANUAL_INPUT_CONTINUATION_FILE="{continuation_file_path}"')

                return
                

        # Compose system prompt.
        system_msg = self.config.system_template.format(**self.system_args)
        system_msg = f"{system_msg}\n\n{self._system_repro_prompt()}"
        # self.logger.info(f"SYSTEM ({self.name})\n{system_msg}")

        self.history: list[dict[str, Any]] = []
        self._append_history({"role": "system", "content": system_msg, "agent": self.name})

        if "history_to_messages" in dir(self.model):
            self.prepare_demos()

    def prepare_demos(self):
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
                demonstration = self.config.demonstration_template.format(demonstration=demo_message)
                self._append_history(
                    {
                        "agent": self.name,
                        "content": demonstration,
                        "is_demo": True,
                        "role": "user",
                    },
                )

    @property
    def state_command(self) -> str:
        """Return the bash command that will be used to extract the environment state."""
        return self.config.state_command.name

    @property
    def local_history(self) -> list[dict[str, str]]:
        """Return the history of the agent since the last reset."""
        result = self.config.history_processor([entry for entry in self.history if entry["agent"] == self.name])
        self._assert_tdd_history_entries(result)
        return result

    def save_trajectory(
        self, trajectory: list[dict[str, Any]], log_path: Path, env_name: str, info: dict[str, Any]
    ) -> None:
        """Save the trajectory"""
        log_dict = {
            "environment": env_name,
            "trajectory": trajectory,
            "history": self.history,
            "info": info,
        }
        try:
            # NOTE: We need `default=vars` since trajectories can now contain typed objects.
            log_path.write_text(json.dumps(log_dict, indent=2, default=vars))
        except Exception as err:
            raise TypeError(f"Failed to save trajectory to '{log_path}':\n  ERROR={err}\n\n  LOGS={repr(log_dict)}")

    def _get_first_match(self, action: str, pattern_type: str) -> re.Match | None:
        """Return the first match of a command pattern in the action string."""
        assert self.config is not None  # mypy
        if pattern_type == "subroutine":
            patterns = {k: v for k, v in self.subroutine_patterns.items()}
        elif pattern_type == "multi_line":
            patterns = {
                k: v
                for k, v in self.command_patterns.items()
                if k in self.config.multi_line_command_endings or k == self.config.submit_command
            }
            patterns += {
                k: v for k, v in self.subroutine_patterns.items() if k in self.config.multi_line_command_endings
            }
        elif pattern_type == "multi_line_no_subroutines":
            patterns = {k: v for k, v in self.command_patterns.items() if k in self.config.multi_line_command_endings}
        else:
            msg = f"Unknown pattern type: {pattern_type}"
            raise ValueError(msg)
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
        parsed_action = list()
        rem_action = action
        while rem_action.strip():
            first_match = self._get_first_match(rem_action, "multi_line_no_subroutines")
            if first_match:
                pre_action = rem_action[: first_match.start()]
                match_action = rem_action[first_match.start() : first_match.end()]
                rem_action = rem_action[first_match.end() :]
                if pre_action.strip():
                    parsed_action.append(pre_action)
                if match_action.strip():
                    eof = first_match.group(3).strip()
                    if not match_action.split("\n")[0].strip().endswith(f"<< '{eof}'"):
                        guarded_command = match_action[first_match.start() :]
                        first_line = guarded_command.split("\n")[0]
                        guarded_command = guarded_command.replace(first_line, first_line + f" << '{eof}'", 1)
                        parsed_action.append(guarded_command)
                    else:
                        parsed_action.append(match_action)
            else:
                parsed_action.append(rem_action)
                rem_action = ""
        return "\n".join(parsed_action)

    def split_actions(self, action: str, pattern_type="subroutine") -> list[dict[str, Any]]:
        """Split an action into a list of actions in a greedy manner, each of which is a subroutine call or a single command."""
        parsed_action = list()
        rem_action = action
        while rem_action.strip():
            first_match = self._get_first_match(rem_action, pattern_type)
            if first_match:
                pre_action = rem_action[: first_match.start()]
                match_action = rem_action[first_match.start() : first_match.end()]
                rem_action = rem_action[first_match.end() :]
                if pre_action.strip():
                    parsed_action.append({"agent": self.name, "action": pre_action, "cmd_name": None})
                if match_action.strip():
                    if match_action.split()[0] == self.config.submit_command:
                        parsed_action.append(
                            {
                                "agent": self.name,
                                "action": match_action,
                                "cmd_name": first_match.group(1),
                            },
                        )  # submit command is not a subroutine
                    else:
                        parsed_action.append(
                            {
                                "agent": first_match.group(1),
                                "args": first_match.group(2),
                                "action": match_action,
                                "cmd_name": first_match.group(1),
                            },
                        )
            else:
                parsed_action.append({"agent": self.name, "action": rem_action, "cmd_name": None})
                rem_action = ""
        return parsed_action

    def _parse_command_patterns(self) -> None:
        assert self.config is not None  # mypy
        self.command_patterns = dict()
        for command in self.config._commands:
            if command.end_name is not None:
                pat = re.compile(
                    rf"^\s*({command.name})\s*(.*?)^({command.end_name})\s*$",
                    re.DOTALL | re.MULTILINE,
                )
                self.command_patterns[command.name] = pat
            else:
                pat = re.compile(rf"^\s*({command.name})\s*(.*?)$", re.MULTILINE)
                self.command_patterns[command.name] = pat
        self.subroutine_patterns = dict()
        for _, subroutine in self.config._subroutines.items():
            if subroutine.end_name is None:
                pat = re.compile(rf"^\s*({subroutine.name})\s*(.*?)$", re.MULTILINE)
                self.subroutine_patterns[subroutine.name,] = pat
            else:
                pat = re.compile(
                    rf"^\s*({subroutine.name})\s*(.*?)^({subroutine.end_name})\s*$",
                    re.DOTALL | re.MULTILINE,
                )
                self.subroutine_patterns[subroutine.name] = pat
        if hasattr(self.config, "submit_command_end_name"):
            submit_pat = re.compile(
                rf"^\s*({self.config.submit_command})\s*(.*?)^({self.config.submit_command_end_name})\s*$",
                re.DOTALL | re.MULTILINE,
            )
        else:
            submit_pat = re.compile(rf"^\s*({self.config.submit_command})(\s*)$", re.MULTILINE)  # group 2 is nothing
        self.subroutine_patterns[self.config.submit_command] = submit_pat
        self.command_patterns[self.config.submit_command] = submit_pat

    def get_command(self, name: str) -> Command | None:
        return next((c for c in self.config._commands if c.name == name), None)

    def forward(self, observation: str, available_actions: list[str], state: str) -> tuple[str, str, ModelQueryResult]:
        """Forwards the model

        Args:
            observation: Observation
            available_actions: Currently not used
            state:

        Returns:
            thought: model reasoning
            action: action that the model proposes
            output: raw model output (not output of the action)
        """
        if self.initial_model_response is not None:
            thought, action, content = itemgetter("thought", "action", "content")(self.initial_model_response)
            output = make_model_query_result(content)
            self.initial_model_response = None
        else:
            thought, action, output = self.forward_with_error_check(observation, state)

        last_tool_name = get_last_valid_tool_use_name(output)
        last_command = self.get_command(last_tool_name)
        ran_tdd_action = last_command.tdd if last_command else False

        if ran_tdd_action:
            # Only keep one tdd entry at a time.
            self._unflag_tdd_history()

        self._append_history(
            {
                "role": "assistant",
                "content": make_assistant_content(output),
                "thought": thought,
                "action": action,
                "agent": self.name,
                "tdd": ran_tdd_action,
            },
        )

        self.logger.info(f"💭 PROMPT-RESULT: THOUGHT ({self.name}): {len(thought)}\n{thought}")
        self.logger.info(f"🎬 ACTION ({self.name})\n{action}")

        return thought, action, output

    def forward_model(self, observation: str, state: str) -> ModelQueryResult:
        """Query the model with the current state and observation with the appropriate template.

        Returns:
            output: raw model output (not output of the command)
        """
        assert self.config is not None  # mypy

        try:
            state_vars = json.loads(state)
        except json.JSONDecodeError as err:
            msg = f"Failed to decode state JSON -\n  INPUT={state}\n  ERROR={err}"
            raise ValueError(msg)

        templates: list[str] = []
        # Determine observation template based on what prior observation was
        is_init = not self.made_initial_prompt
        if is_init:
            # Show instance template if prev. obs. was initial system message
            self.made_initial_prompt = True
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
        for template in templates:
            messages.append(
                template.format(
                    **self.instance_args,
                    **self.system_args,
                    **state_vars,
                    observation=(observation if observation is not None else ""),
                ),
            )

        message = "\n".join(messages)

        self.logger.info(f"🤖 MODEL INPUT\n{message}")
        self._append_history(
            {
                "role": "user",
                "content": make_user_reply_content(message, None, self.history, False),
                "agent": self.name,
                "tdd": self.env.tdd and is_init,
            }
        )

        for hook in self.hooks:
            hook.on_model_query(query=self.local_history, agent=self.name)
        return self.model.query(self.local_history)

    def retry_after_format_fail(self, output: ModelQueryResult) -> ModelQueryResult:
        """Ask the model to correct (without committing to persistent history) after a malformatted model output"""
        format_error_template = self.config.format_error_template

        self.logger.warning(f"PROMPT-RESULT: MALFORMED OUTPUT\n{repr(output)}")
        self.logger.warning(f"FORMAT ERROR\n{format_error_template}")

        temp_history = self.local_history + [
            {"role": "assistant", "content": make_assistant_content(output), "agent": self.name},
            {"role": "user", "content": make_user_reply_content(format_error_template, output, self.history, True), "agent": self.name},
        ]
        return self.model.query(temp_history)

    def retry_after_blocklist_fail(self, output: ModelQueryResult, action: str) -> ModelQueryResult:
        """Ask the model to correct (without committing to persistent history) after a disallowed command"""
        name = action.strip().split()[0]
        blocklist_error_message = self.config.blocklist_error_template.format(name=name)

        self.logger.warning(f"PROMPT-RESULT: BLOCKLISTED OUTPUT\n{repr(output)}")
        self.logger.warning(f"BLOCKLIST ERROR\n{blocklist_error_message}")

        temp_history = self.local_history + [
            {"role": "assistant", "content": make_assistant_content(output), "agent": self.name},
            {"role": "user", "content": make_user_reply_content(blocklist_error_message, output, self.history, True), "agent": self.name},
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
        return False

    def check_format_and_requery(
        self,
        output: ModelQueryResult,
    ) -> tuple[str, str, ModelQueryResult]:
        """Query the model with the current state and observation with the appropriate template.

        Try to parse the output into a thought and action. Retry if the output is malformatted or the action is blocked.

        Returns:
            thought: model reasoning
            action: action that the model proposes
            output: raw model output
        """
        # Condition for handling outputs with no thought (just action)
        if self.model.args.model_name == "human":
            return "", output, output
        elif self.model.args.model_name == "human_thought":
            thought, action = ParseFunction.get("ThoughtActionParser")(
                output,
                self.config._commands + self.config.subroutine_types,
                strict=False,
            )
            return thought, action, output

        format_fails = blocklist_fails = 0

        while format_fails + blocklist_fails <= 2:
            try:
                thought, action = self.config.parse_function(
                    output,
                    self.config._commands + self.config.subroutine_types,
                    strict=False,
                )
            except KeyboardInterrupt:
                raise
            except FormatError as err:
                format_fails += 1
                logger.error(f"[check_format_and_requery] failed to parse output:\n  ERROR={err}\n\nOUTPUT={repr(output)}")
                output = self.retry_after_format_fail(output)
                continue
            if self.should_block_action(action):
                blocklist_fails += 1
                output = self.retry_after_blocklist_fail(output, action)
            else:
                return thought, action, output
        self.logger.warning(f"Malformat limit reached: \n{repr(output)}")
        return "Exit due to format error", "exit_format", output

    def forward_with_error_check(self, observation: str, state: str) -> tuple[str, str, ModelQueryResult]:
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

    def init_environment_vars(self, env: SWEEnv):
        self.set_environment_vars(env, self.config.env_variables)

    def set_environment_vars(self, env: SWEEnv, env_variables: dict[str, Any]) -> None:
        # Init REPO and assure that the bot constrains its works to that folder.
        assert self.config is not None  # mypy
        commands_to_execute = (
            [self.config.state_command.code]
            +
            # [code for code in self.config.util_functions] +
            # [command.code for command in self.config._commands] +
            [f"{k}={v}" for k, v in env_variables.items()]
        )
        commands = "\n".join(commands_to_execute)
        try:
            output = env.communicate(commands)
            if env.returncode != 0:
                msg = f"Nonzero return code: {env.returncode}\nOutput: {output}"
                raise RuntimeError(msg)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.logger.warning("Failed to set environment variables")
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
        env.add_commands(command_files)

    def get_environment_vars(self, env: SWEEnv) -> dict[str, Any]:
        """Get environment variables"""
        assert self.config is not None  # mypy
        env_vars = dict()
        for var in self.config.env_variables:
            env_vars[var] = env.communicate(f"echo ${var}").strip()
        return env_vars

    def call_subroutine(self, agent_name: str, sub_action, env: SWEEnv):
        """Call subroutine"""
        assert self.config is not None  # mypy
        env_vars = self.get_environment_vars(env)
        cwd = env.communicate("pwd -P").strip()
        init_observation = self.config._subroutines[agent_name].init_observation
        if init_observation is not None:
            obs, _, _, _ = env.step(init_observation.format(args=sub_action["args"]))
        else:
            obs = None
        if env.returncode != 0:
            self._append_history({"role": "user", "content": obs, "agent": agent_name})
            msg = f"Nonzero return code: {env.returncode} for init_observation in {agent_name}.\n{obs}"
            raise RuntimeError(msg)
        return_type = self.config._subroutines[agent_name].return_type
        sub_agent = Agent(agent_name, self.config._subroutines[agent_name].agent_args)
        sub_agent_output = sub_agent.run(
            {"issue": sub_action["args"]},
            env,
            observation=obs,
            return_type=return_type,
            init_model_stats=self.model.stats,
        )
        self.history += sub_agent.history
        self.set_environment_vars(env, env_vars)
        env.communicate(f"cd {cwd}")
        self.model.stats.replace(sub_agent.model.stats)
        return sub_agent_output

    @instrument("Agent#run", params=["setup_args", "env", "observation", "traj_dir", "return_type", "init_model_stats"])
    def run(
        self,
        setup_args: dict[str, Any],
        env: SWEEnv,
        observation: str | None = None,
        traj_dir: Path | None = None,
        return_type: str | None = "info_trajectory",
        init_model_stats: APIStats | None = None,
    ):
        """
        Run the agent on an environment.
        Return the final value of the specified return type.

        Args:
            setup_args: Arguments to pass to the agent's setup method.
            env: The environment to run the agent on.
            observation: Output from environment setup
            traj_dir: Directory to save the trajectory to
            return_type: Controls what to return.
                This should be left at `info_trajectory`, the
                other values are for internal usage with subroutines.
            init_model_stats: Initial model stats to use for the run.

        Returns:
            If return_type is "info_trajectory", returns a tuple of
            the info dictionary and the trajectory (list of dictionaries).
        """
        done = False
        # mypy checks
        assert env.container_obj is not None
        assert env.record is not None
        assert self.config is not None

        self.made_initial_prompt = False
        self.manual_input.set_instance_id(env.record["instance_id"])

        if env.container_obj.id != self.last_container_id:
            self.logger.info(f"Initializing agent settings for container {env.container_obj.id}")
            self.init_environment_vars(env)
            self.last_container_id = env.container_obj.id
        # Re-initialize primary
        self.setup(env, setup_args, init_model_stats)

        for hook in self.hooks:
            hook.on_run_start()

        # Run action/observation loop
        trajectory = []
        info = {}
        traj_log_path = traj_dir / (env.record["instance_id"] + ".traj")
        self.logger.info("Trajectory will be saved to %s", traj_log_path)
        while not done:
            for hook in self.hooks:
                hook.on_step_start()
            state = env.communicate(self.state_command) if self.state_command else None
            stop_on_tdd_repro = self.manual_input.enabled() and self.initial_model_response is None
            thought, action, output = self.forward(observation, env.get_available_actions(), state)
            for hook in self.hooks:
                hook.on_actions_generated(thought=thought, action=action, output=repr(output))
            observations = list()
            run_action = self._guard_multiline_input(action)
            for sub_action in self.split_actions(run_action):
                if sub_action["agent"] == self.name or sub_action["cmd_name"] == self.config.submit_command:
                    for hook in self.hooks:
                        hook.on_sub_action_started(sub_action=sub_action)
                    obs, _, done, info = env.step(sub_action["action"])
                    for hook in self.hooks:
                        hook.on_sub_action_executed(obs=obs, done=done)
                    observations.append(obs)
                    if sub_action["cmd_name"] == self.config.submit_command:
                        done = True
                    if sub_action["action"] == "tdd_repro" and stop_on_tdd_repro:
                        done = True
                        output = env.communicate("([ -s /root/test.patch ] && git apply -R < /root/test.patch); git add -A && echo -n '<<CONVERSATION_PATCH||' > /root/conversation-patch && git diff --cached >> /root/conversation-patch && echo -n '||CONVERSATION_PATCH>>' >> /root/conversation-patch && cat /root/conversation-patch")

                        pattern = r"\<\<CONVERSATION_PATCH\|\|(.*)\|\|CONVERSATION_PATCH\>\>"

                        match = re.search(pattern, output, re.DOTALL)
                        if match is not None:
                            patch = match.group(1)
                            self.manual_input.save_conversation(self.history, patch)
                    if done:
                        break
                else:
                    # We don't expect agent subroutines to be a thing (at least we are not prepared for them):
                    logger.warning(f"WARNING: unexpected call_subroutine: {repr(sub_action)}")
                    agent_name = sub_action["agent"]
                    sub_agent_output = self.call_subroutine(agent_name, sub_action, env)
                    observations.append(sub_agent_output)

            observation = "\n".join([obs for obs in observations if obs is not None])

            trajectory_step = TrajectoryStep(
                {
                    "action": action,
                    "observation": observation,
                    "response": output,
                    "state": state,
                    "thought": thought,
                },
            )
            trajectory.append(trajectory_step)
            model_stats: APIStats = self.model.stats
            info["model_stats"] = model_stats.to_dict()
            if traj_dir:
                self.save_trajectory(trajectory, traj_log_path, env_name=env.name, info=info)
            for hook in self.hooks:
                hook.on_step_done(trajectory_step=trajectory_step, model_stats=model_stats)

        for hook in self.hooks:
            hook.on_run_done()

        self.logger.info("Trajectory saved to %s", traj_log_path)

        if return_type == "info":
            return info
        if return_type == "info_trajectory":
            return info, trajectory
        return trajectory[-1][return_type]
