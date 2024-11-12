from __future__ import annotations

import copy
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field
from simple_parsing.helpers.fields import field
from tenacity import RetryError

from sweagent import __version__, get_agent_commit_hash
from sweagent.agent.history_processors import DefaultHistoryProcessor, HistoryProcessor
from sweagent.agent.hooks.abstract import AbstractAgentHook, CombinedAgentHook
from sweagent.agent.models import (
    AbstractModel,
    APIStats,
    ContextWindowExceededError,
    CostLimitExceededError,
    HumanModel,
    ModelConfig,
    get_model,
)
from sweagent.environment.config.problem_statement import ProblemStatement, ProblemStatementConfig
from sweagent.environment.swe_env import SWEEnv
from sweagent.tools.parsing import FormatError
from sweagent.tools.tools import ToolConfig, ToolHandler
from sweagent.types import AgentInfo, AgentRunResult, History, HistoryItem, Trajectory, TrajectoryStep
from sweagent.utils.config import _convert_paths_to_abspath
from sweagent.utils.log import get_logger
from sweagent.utils.patch_formatter import PatchFormatter


class TemplateConfig(BaseModel):
    """This configuration is used to define almost all message templates that are
    formatted by the agent and sent to the LM.
    """

    system_template: str = ""
    instance_template: str = ""
    next_step_template: str = "Observation: {observation}"

    next_step_no_output_template: str = None  # type: ignore
    """Template for the next step when the last output was empty. Defaults to next_step_template."""

    strategy_template: str | None = None
    demonstration_template: str | None = None

    demonstrations: list[Path] = field(default_factory=list)
    """Paths to demonstrations. If path is not absolute, it is assumed to be
    relative to the SWE_AGENT_CONFIG_ROOT (if set) or the SWE-agent repository root
    """

    put_demos_in_history: bool = False
    """If True, add demonstration to history instead of as a single message"""

    def model_post_init(self, __context):
        self.demonstrations = _convert_paths_to_abspath(self.demonstrations)
        if self.next_step_no_output_template is None:
            self.next_step_no_output_template = self.next_step_template


class AgentConfig(BaseModel):
    name: str = "main"
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    history_processor: HistoryProcessor = Field(default_factory=DefaultHistoryProcessor)
    model: ModelConfig

    # pydantic config
    model_config = ConfigDict(extra="forbid")


# todo: separate out from_config. In particular separate out model (as a class, etc.). Agent should only take templates, tools, history processor and model.
#    slight problem: get_model needs commands....
class Agent:
    def __init__(
        self,
        *,
        templates: TemplateConfig,
        tools: ToolHandler,
        history_processor: HistoryProcessor,
        model: AbstractModel,
        name: str = "main",
        _catch_errors: bool = True,
        _always_require_zero_exit_code: bool = False,
    ):
        """The agent handles the behaviour of the model and how it interacts with the environment.

        To run the agent, either call `self.run` or `self.setup` and then `self.step` in a loop.
        """
        self._catch_errors = _catch_errors
        self._always_require_zero_exit_code = _always_require_zero_exit_code
        self.name = name
        self.model = model
        self.templates = templates
        self.tools = tools
        self.history_processor = history_processor

        self.logger = get_logger("agent", emoji="🤠")

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

        self._chook = CombinedAgentHook()

    @classmethod
    def from_config(cls, config: AgentConfig) -> Self:
        model = get_model(config.model, config.tools.commands)
        return cls(
            templates=config.templates,
            tools=ToolHandler.from_config(config.tools),
            history_processor=config.history_processor,
            model=model,
        )

    def add_hook(self, hook: AbstractAgentHook) -> None:
        """Add hook to agent"""
        hook.on_init(agent=self)
        self._chook.add_hook(hook)

    # Properties
    # ----------

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

    @property
    def local_history(self) -> list[dict[str, str]]:
        """Return the history of the agent since the last reset."""
        return self.history_processor([entry for entry in self.history if entry["agent"] == self.name])

    # Methods
    # -------

    def _append_history(self, item: HistoryItem) -> None:
        """Adds an item to the history."""
        self._chook.on_query_message_added(**item)
        self.history.append(item)

    def setup(
        self,
        env: SWEEnv,
        problem_statement: ProblemStatement | ProblemStatementConfig,
        output_dir: Path = Path("."),
    ) -> None:
        """Setup the agent for a new instance. This includes
        formatting the system message and adding demonstrations to the history.

        This method is called by `self.run`.

        Args:
            instance_args: Arguments for the instance
        """
        self._problem_statement = problem_statement
        self._env = env

        # Save/reset some attributes
        self.info = AgentInfo()
        self.info["swe_agent_hash"] = get_agent_commit_hash()
        self.info["swe_agent_version"] = __version__
        self.traj_path = output_dir / (self._problem_statement.id + ".traj")
        self.logger.info("Trajectory will be saved to %s", self.traj_path)

        self._i_attempt = 0
        self._history_by_attempt = defaultdict(list)
        self._trajectory_by_attempt = defaultdict(list)
        self._info_by_attempt = defaultdict(dict)  # type: ignore
        self._forwarded_vars = {}
        # if self._rloop is not None:
        #     self._forwarded_vars = self._rloop.get_forwarded_vars()
        self.tools.install(self._env)
        self.setup_attempt()

        self._chook.on_setup_done()

    def setup_attempt(self) -> None:
        """Setup the agent for a new attempt. This includes resetting the model stats."""
        if self._i_attempt > 0:
            assert self._env is not None  # mypy
            self._env.reset()
        self.model.reset_stats()
        self.add_system_message_to_history()
        self.add_demonstrations_to_history()

    def add_system_message_to_history(self) -> None:
        """Add system message to history"""
        assert self._problem_statement is not None
        system_msg = self.templates.system_template.format(
            command_docs=self.tools.config.command_docs,
            **self.tools.config.env_variables,
            problem_statement=self._problem_statement.get_problem_statement(),
        )
        self.logger.info(f"SYSTEM ({self.name})\n{system_msg}")
        self._append_history(HistoryItem({"role": "system", "content": system_msg, "agent": self.name}))

    def add_demonstrations_to_history(self) -> None:
        """Add demonstrations to history"""
        for demonstration_path in self.templates.demonstrations:
            self._add_demonstration_to_history(demonstration_path)

    def _add_demonstration_to_history(self, demonstration_path: Path) -> None:
        """Load demonstration from disk and add to history"""
        if self.templates.demonstration_template is None and not self.templates.put_demos_in_history:
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

        if self.templates.put_demos_in_history:
            if self.templates.demonstration_template is not None:
                self.logger.warning("Demonstration template is ignored for put_demos_in_history=True")
            # Add demonstration to history directly as separate messages
            for entry in demo_history:
                if entry["role"] != "system":
                    entry["is_demo"] = True
                    self._append_history(entry)
        else:
            # Add demonstration as single message to history
            demo_history = [entry for entry in demo_history if entry["role"] != "system"]
            demo_message = "\n".join([entry["content"] for entry in demo_history])
            assert self.templates.demonstration_template is not None
            demonstration = self.templates.demonstration_template.format(demonstration=demo_message)
            self._append_history(
                {
                    "agent": self.name,
                    "content": demonstration,
                    "is_demo": True,
                    "role": "user",
                },
            )

    def add_to_history(self, observation: str, state: dict[str, str]) -> None:
        """Add observation to history, as well as the instance template or demonstrations if we're
        at the start of a new attempt.
        """
        templates: list[str] = []
        # Determine observation template based on what prior observation was
        if self.history[-1]["role"] == "system" or self.history[-1].get("is_demo", False):
            # Show instance template if prev. obs. was initial system message
            templates = [self.templates.instance_template]
            if self.templates.strategy_template is not None:
                templates.append(self.templates.strategy_template)
        elif observation is None or observation.strip() == "":
            # Show no output template if observation content was empty
            templates = [self.templates.next_step_no_output_template]
        else:
            # Show standard output template if there is observation content
            templates = [self.templates.next_step_template]

        # Populate selected template(s) with information (e.g., issue, arguments, state)
        messages = []
        assert self._problem_statement is not None

        format_dict = dict(
            command_docs=self.tools.config.command_docs,
            **self.tools.config.env_variables,
            **state,
            observation=observation or "",
            **self._forwarded_vars,
            problem_statement=self._problem_statement.get_problem_statement(),
        )

        for template in templates:
            try:
                messages.append(
                    template.format(**format_dict),
                )
            except KeyError:
                self.logger.debug("The following keys are available: %s", format_dict.keys())
                raise

        message = "\n".join(messages)

        self.logger.info(f"🤖 MODEL INPUT\n{message}")
        self._append_history({"role": "user", "content": message, "agent": self.name})

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

    def forward_model(self, observation: str, state: dict[str, str]) -> tuple[str, str, str]:
        """This method is called by `self.step`. It forwards the model
        and checks the output for malformattings or blocked actions.

        Args:
            observation: Observation from the last step
            state: Environment state as extracted by the state commands.

        Returns:
            thought: model reasoning
            action: action that the model proposes
            output: raw model output (not output of the action)
        """
        self.add_to_history(observation, state)
        self._chook.on_model_query(messages=self.local_history, agent=self.name)
        try:
            output = self.model.query(self.local_history)
            thought, action, output = self.check_format_and_requery(output)
        except KeyboardInterrupt:
            raise
        except RuntimeError as e:
            self.logger.exception(f"Runtime error: {e}")
            return (
                f"Exit due to runtime error: {e}",
                "exit_error",
                f"exit due to runtime error: {e}",
            )
        except ContextWindowExceededError as e:
            self.logger.error("Context window exceeded: %s", e)
            return "Exit due to context window", "exit_context", "Exit due to context window"
        except CostLimitExceededError as e:
            self.logger.error("Cost limit exceeded: %s", e)
            return "Exit due to cost limit", "exit_cost", "Exit due to cost limit"
        except RetryError as e:
            self.logger.error("Retry error: %s", e)
            return (
                f"Exit due to retry error: {e}",
                "exit_api",
                f"exit due to retry error: {e}",
            )

        self._append_history(
            {
                "role": "assistant",
                "content": output,
                "thought": thought,
                "action": action,
                "agent": self.name,
            },
        )
        self.logger.info(f"💭 THOUGHT\n{thought}\n🎬 ACTION\n{action.strip()}")

        return thought, action, output

    def retry_after_format_fail(self, output: str) -> str:
        """Ask the model to correct after a malformatted model output.

        This involves adding temporary history based on the error template and querying the model.
        If the model is able to correct itself, the records of the mistakes will not be part of the history
        (but they are saved in the trajectory).
        """
        format_error_template = self.tools.config.format_error_template

        self.logger.warning(f"MALFORMED OUTPUT\n{output}")
        self.logger.warning(f"FORMAT ERROR\n{format_error_template}")

        temp_history = self.local_history + [
            {"role": "assistant", "content": output, "agent": self.name},
            {"role": "user", "content": format_error_template, "agent": self.name},
        ]
        return self.model.query(temp_history)

    def retry_after_blocklist_fail(self, output: str, action: str) -> str:
        """Ask the model to correct after a disallowed command

        This involves adding temporary history based on the error template and querying the model.
        If the model is able to correct itself, the records of the mistakes will not be part of the history
        (but they are saved in the trajectory).
        """
        name = action.strip().split()[0]
        blocklist_error_message = self.tools.config.filter.blocklist_error_template.format(name=name)

        self.logger.warning(f"BLOCKLISTED OUTPUT\n{output}")
        self.logger.warning(f"BLOCKLIST ERROR\n{blocklist_error_message}")

        temp_history = self.local_history + [
            {"role": "assistant", "content": output, "agent": self.name},
            {"role": "user", "content": blocklist_error_message, "agent": self.name},
        ]
        return self.model.query(temp_history)

    def check_format_and_requery(
        self,
        output: str,
    ) -> tuple[str, str, str]:
        """Checks model output. If the output is malformatted or the action is blocked, call
        `self.retry_after_format_fail` or `self.retry_after_blocklist_fail`, else return
        parsed output.

        Try to parse the output into a thought and action. Retry if the output is malformatted or the action is blocked.

        Returns:
            thought: model reasoning
            action: action that the model proposes
            output: raw model output
        """
        # Condition for handling outputs with no thought (just action)
        if isinstance(self.model, HumanModel):
            # Need special attention, because HumanModel doesn't know how to format actions
            # because it depends on the action parser in tools
            return "", output, output

        format_fails = blocklist_fails = 0

        while format_fails + blocklist_fails <= 2:
            try:
                thought, action = self.tools.parse_actions(
                    output,
                )
            except KeyboardInterrupt:
                raise
            except FormatError:
                format_fails += 1
                output = self.retry_after_format_fail(output)
                continue
            if self.tools.should_block_action(action):
                blocklist_fails += 1
                output = self.retry_after_blocklist_fail(output, action)
            else:
                return thought, action, output
        self.logger.warning(f"Malformat limit reached: \n{output}")
        return "Exit due to format error", "exit_format", output

    # todo: add a hook here
    def handle_special_actions(self, action: str, info: AgentInfo) -> tuple[str, bool, AgentInfo] | None:
        """Handles special actions like `skip`, `exit_cost`, etc."""
        assert self._env is not None
        assert self.tools is not None
        if action == "skip":
            observation = "Skipped"
            info["exit_status"] = "skipped"
            return observation, True, info
        if action == "exit_forfeit":
            observation = "Exited"
            info["exit_status"] = action
            return observation, True, info
        if action in {"exit_context", "exit_cost", "exit_error", "exit_format", "exit_api"}:
            try:
                return self.attempt_autosubmission_after_error(action, info)
            except KeyboardInterrupt:
                raise
            except:
                observation = "Exited"
                info["exit_status"] = action
                return observation, True, info
        return None

    def attempt_autosubmission_after_error(self, action: str, info: AgentInfo) -> tuple[str, bool, AgentInfo]:
        """If we hit exit_cost or similar exit statuses, we attempt to still extract the patch/submission
        and submit this. This means we send the `submit` command to the runtime and parse the output.
        """
        assert self._env is not None
        assert self.tools is not None
        observation = self._env.communicate(input="submit")
        submission = self.tools.parse_submission_cmd_output(observation)
        assert submission is not None and submission.strip() != "", AssertionError("No submission found.")
        self.logger.info(f"Found submission: {submission}")
        info["exit_status"] = f"submitted ({action})"
        info["submission"] = submission
        info.update(self._get_edited_files_with_context(patch=submission))  # type: ignore
        observation = "Exited (autosubmitted)"
        self.logger.info("Exiting with autosubmission")
        return observation, True, info

    def handle_submission(self, observation: str, info: AgentInfo) -> tuple[str, bool, AgentInfo] | None:
        """Check if there was a submission in the observation and handle it.

        Returns:
            None if no submission was found, else tuple of observation, done, info
        """
        assert self.tools is not None
        submission = self.tools.parse_submission_cmd_output(observation)
        if submission is None:
            return None
        self.logger.info(f"Found submission: {submission}")
        info["exit_status"] = "submitted"
        info["submission"] = submission if submission.strip() != "" else None
        info.update(self._get_edited_files_with_context(patch=submission))  # type: ignore
        observation = submission if submission.strip() != "" else ""
        return observation, True, info

    def _get_edited_files_with_context(self, patch: str) -> dict[str, str]:
        """Get the edited files with context from the patch"""
        assert self._env is not None
        pf = PatchFormatter(patch, read_method=self._env.read_file) if patch else None
        out = {}
        for context_length in [30, 50, 70]:
            value = "Empty. No edited files found."
            if pf is not None:
                value = pf.get_files_str(original=False, context_length=context_length)
            out[f"edited_files{context_length}"] = value
        return out

    def execute_action_in_runtime(self, action: str, info: AgentInfo) -> tuple[str, bool, AgentInfo]:
        assert self._env is not None
        # Attempt to run action in container
        try:
            observation = self._env.communicate(
                input=action,
                timeout=self.tools.config.execution_timeout,
                set_last_action=True,
                check=self._always_require_zero_exit_code,
            )
        except RuntimeError as e:
            if not self._catch_errors:
                self._env.close()
                raise
            observation = e.args[1] if len(e.args) > 1 else ""
            observation += "COMMAND FAILED TO EXECUTE. RESTARTING PROCESS."
            info["exit_status"] = "exit_environment_error"
            self.logger.warning(f"Failed to execute command: {e}\nRESTARTING PROCESS.")
            self._env.close()
            return observation, True, info
        # todo: Should this also be handled in the exit status?
        except Exception:
            if not self._catch_errors:
                self._env.close()
                raise
            self._env.close()
            observation = "Unknown exception"
            self.logger.exception("Unknown exception")
            return observation, True, info

        # Check if there was a submission
        submission_result = self.handle_submission(observation, info)
        if submission_result is not None:
            return submission_result

        return observation, False, info

    def handle_action(self, action: str) -> tuple[str, bool, AgentInfo]:
        """Runs an action proposed by the agent in the environment and returns the corresponding output.

        Args:
            action: command to run in bash shell

        Returns:
            observation:  output from container
            done: whether task is over
            info: additional information (e.g. debugging information)
        """
        info: AgentInfo = {}
        # Make sure to have the right keys even if the submission is missing/empty
        info.update(self._get_edited_files_with_context(patch=""))  # type: ignore

        # Handle special actions
        special_action_result = self.handle_special_actions(action, info)
        if special_action_result is not None:
            return special_action_result

        return self.execute_action_in_runtime(action, info)

    def step(self, observation: str) -> tuple[str, bool]:
        """Run a step of the agent:

        1. Take the last observation, combine it with all other context
           (i.e., the history of thoughts and actions). This is done by
           `self.forward`.
        2. Execute the action and return the new observation. This is done by
           `self._env.step`.
        3. Save the new trajectory etc.

        Returns:
            observation: Observation
            done: Whether `submit` or another exit reason was called
        """

        assert self._env is not None

        # Forward model and get actions
        self._chook.on_step_start()
        state = self.tools.get_state(env=self._env)
        thought, raw_action, output = self.forward_model(observation, state)
        self._chook.on_actions_generated(thought=thought, action=raw_action, output=output)
        run_action: str = self.tools.guard_multiline_input(raw_action).strip()

        # Execute action
        execution_t0 = time.perf_counter()
        self._chook.on_action_started(action=run_action)
        observation, done, _info = self.handle_action(run_action)
        self.info.update(_info)
        self._chook.on_action_executed(obs=observation, done=done)
        execution_time = time.perf_counter() - execution_t0

        # Bookkeeping
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
        self.info["model_stats"] = model_stats.model_dump()
        self._chook.on_step_done(trajectory_step=trajectory_step, model_stats=model_stats)
        return observation, done

    # todo: Set env already in __init__, i.e., initialize a new agent class for every instance?
    def run(
        self,
        env: SWEEnv,
        problem_statement: ProblemStatement | ProblemStatementConfig,
        output_dir: Path = Path("."),
    ) -> AgentRunResult:
        """Run the agent on a problem instance. This method contains the
        main loop that repeatedly calls `self._step` until the problem is solved.

        Args:
            setup_args: Arguments to pass to the agent's setup method.
            env: The environment to run the agent on.
            traj_dir: Directory to save the trajectory to
            init_model_stats: Initial model stats to use for the run.
        """
        self.setup(env=env, problem_statement=problem_statement, output_dir=output_dir)

        # Run action/observation loop
        self._chook.on_run_start()
        done = False
        observation = ""
        while not done:
            observation, done = self.step(observation)
            self.save_trajectory()
        self._chook.on_run_done(trajectory=self.trajectory, info=self.info)

        self.logger.info("Trajectory saved to %s", self.traj_path)

        return AgentRunResult(info=self.info, trajectory=self.trajectory)
