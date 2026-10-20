"""[cyan][bold]Replay a trajectory file.[/bold][/cyan]

[cyan][bold]=== DESCRIPTION ===[/bold][/cyan]

We will take all actions in the trajectory and execute them in an environment.

This has two main use cases:

1. Create a demo from a yaml file containing actions (can also be created from a trajectory file with [green]sweagent run traj-to-demo[/green]).
   [green]run-replay[/green] will execute the actions to get the environment output and produce a full trajectory to be used as a demo.
2. Debugging and testing of tools and environment behavior.

[cyan][bold]=== EXAMPLES ===[/bold][/cyan]

Replay a trajectory file:

[green]sweagent run replay --traj_path mytraj.traj[/green]

Replay a demo file:

[green]sweagent run replay --traj_path mydemo.demo.yaml[/green]

[cyan][bold]=== DEPLOYMENT HANDLING ===[/bold][/cyan]

Trajectory files embed the deployment configuration of the run that recorded them.
Because trajectories are shared as data files, the embedded deployment is only
honored if it is identical to the local default deployment, or if you explicitly
opt in with [green]--deployment_from_traj true[/green] (or override it with [green]--deployment[/green]).
Otherwise, replay runs on the local default deployment and prints a warning.

Honoring a deployment received with a trajectory (e.g. to reproduce a run on
another machine):

[green]sweagent run replay --traj_path their.traj --deployment_from_traj true[/green]
"""

import json
import sys
import tempfile
from getpass import getuser
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from swerex.deployment.abstract import AbstractDeployment
from swerex.deployment.config import DeploymentConfig, get_deployment
from typing_extensions import Self

from sweagent.agent.agents import DefaultAgent
from sweagent.agent.models import ReplayModelConfig
from sweagent.environment.swe_env import EnvironmentConfig, SWEEnv
from sweagent.run.common import BasicCLI, ConfigHelper
from sweagent.run.run_single import RunSingle, RunSingleConfig
from sweagent.utils.config import load_environment_variables
from sweagent.utils.log import get_logger


def _describe_deployment(deployment: DeploymentConfig) -> str:
    """Human-readable summary of a deployment config for warnings and prompts."""
    parts = [f"type={deployment.type!r}"]
    image = getattr(deployment, "image", None)
    if image is not None:
        parts.append(f"image={image!r}")
    docker_args = getattr(deployment, "docker_args", None)
    if docker_args:
        parts.append(f"docker_args={docker_args!r}")
    return ", ".join(parts)


class RunReplayConfig(BaseSettings, cli_implicit_flags=False):
    traj_path: Path
    deployment: DeploymentConfig | None = None
    """Override the deployment in the trajectory."""
    deployment_from_traj: bool = False
    """Honor the deployment configuration embedded in the trajectory file instead of
    the local default deployment. Off by default: trajectory files are shared as data
    files, and their embedded deployment selects where the recorded actions run
    (host-local execution for type 'local', arbitrary `docker run` arguments via
    `docker_args`). Has no effect if --deployment is given."""
    output_dir: Path = Path("DEFAULT")
    env_var_path: Path | None = None
    """Path to a .env file to load environment variables from."""
    update_config: list[Path] = []
    """Additional config files to merge with the replay config."""

    # pydantic config
    model_config = SettingsConfigDict(extra="forbid", env_prefix="SWE_AGENT_")

    def model_post_init(self, __context: Any) -> None:
        if self.output_dir == Path("DEFAULT"):
            user_id = getuser()
            self.output_dir = Path.cwd() / "trajectories" / user_id / f"replay___{self.traj_path.stem}"
        self.output_dir.mkdir(parents=True, exist_ok=True)


class RunReplay:
    def __init__(
        self,
        *,
        traj_path: Path,
        deployment: AbstractDeployment | None,
        output_dir: Path,
        update_config: list[Path] | None = None,
        deployment_from_traj: bool = False,
        _catch_errors: bool = False,
        _require_zero_exit_code: bool = False,
    ):
        self.traj_path = traj_path
        self.output_dir = output_dir
        self._replay_action_trajs_path = Path(tempfile.NamedTemporaryFile(suffix=".json").name)
        self.logger = get_logger("swea-run", emoji="🏃")
        self._catch_errors = _catch_errors
        self._require_zero_exit_code = _require_zero_exit_code
        self._update_config = update_config if update_config is not None else []

        if traj_path.suffix == ".yaml":
            self._traj_data = yaml.safe_load(traj_path.read_text())
        else:
            self._traj_data = json.loads(traj_path.read_text())
        self.config = self._get_config_from_agent(self._traj_data)

        if deployment is not None:
            # Explicitly chosen by the user (--deployment or programmatic use): no gating.
            self.deployment = deployment
        else:
            self.deployment = get_deployment(self._resolve_deployment_config(deployment_from_traj=deployment_from_traj))

    def _resolve_deployment_config(self, *, deployment_from_traj: bool) -> DeploymentConfig:
        """Decide which deployment config a replay may use.

        The deployment embedded in the trajectory's replay_config is untrusted
        input: trajectory files are exchanged as data (debugging, demonstrations),
        but their embedded deployment selects where the recorded actions execute,
        e.g. host-local subprocesses for type 'local' or arbitrary `docker run`
        arguments via `docker_args`. It is therefore only honored if it is
        identical to the local default deployment, if the user opted in via
        `deployment_from_traj`, or after interactive confirmation. In all other
        cases the local default deployment is used and a warning is logged.
        """
        embedded = self.config.env.deployment
        default = EnvironmentConfig().deployment
        if embedded == default:
            return default
        if deployment_from_traj:
            return embedded
        if sys.stdin.isatty():
            answer = input(
                f"Trajectory {self.traj_path.name!r} embeds a non-default deployment "
                f"({_describe_deployment(embedded)}).\n"
                "Replaying executes the recorded actions there. Honor it? [y/N] "
            )
            if answer.strip().lower() in {"y", "yes"}:
                return embedded
        self.logger.warning(
            "Ignoring deployment embedded in %s (%s): a trajectory is a data file, but "
            "its embedded deployment selects where replayed actions execute (host-local "
            "execution, container image, or docker arguments). Replaying with the local "
            "default deployment (%s) instead. Pass --deployment_from_traj true to honor "
            "the embedded deployment, or --deployment to choose one explicitly.",
            self.traj_path,
            _describe_deployment(embedded),
            _describe_deployment(default),
        )
        return default

    def _get_config_from_agent(self, traj_data):
        try:
            if isinstance(traj_data["replay_config"], str):
                traj_data["replay_config"] = json.loads(traj_data["replay_config"])
            config = RunSingleConfig.model_validate(traj_data["replay_config"])
        except KeyError:
            msg = "Replay config not found in trajectory. Are you running on an old trajectory?"
            raise ValueError(msg)

        # Merge any additional config files
        for config_path in self._update_config:
            update_data = yaml.safe_load(config_path.read_text())
            # Store the current model config before merging
            current_model = config.agent.model
            # Convert the merged data back to a RunSingleConfig
            config_dict = config.model_dump(mode="json")
            merged_dict = config_dict | update_data

            # Ensure agent.model is preserved if not explicitly updated
            if "agent" in merged_dict and "model" not in merged_dict["agent"]:
                merged_dict["agent"]["model"] = current_model.model_dump(mode="json")

            config = RunSingleConfig.model_validate(merged_dict)

        config.agent.model = ReplayModelConfig(replay_path=self._replay_action_trajs_path)
        return config

    @property
    def instance_id(self) -> str:
        return Path(self.traj_path).stem

    @classmethod
    def from_config(cls, config: RunReplayConfig, **kwargs) -> Self:
        load_environment_variables(config.env_var_path)
        return cls(
            traj_path=config.traj_path,
            deployment=get_deployment(config.deployment) if config.deployment else None,
            output_dir=config.output_dir,
            update_config=config.update_config,
            deployment_from_traj=config.deployment_from_traj,
            **kwargs,
        )

    def _create_actions_file(self) -> None:
        # Verify config compatibility with tool calls
        has_tool_calls = any(
            "tool_calls" in item and item["tool_calls"] is not None
            for item in self._traj_data["history"]
            if item["role"] == "assistant"
        )

        agent_config = self.config.agent
        parse_function = agent_config.tools.parse_function.type
        use_function_calling = parse_function == "function_calling"

        if has_tool_calls and not use_function_calling:
            msg = (
                "Trajectory contains tool calls but config is not set up for function calling. "
                "Check that the config you want to use has agent.tools.parse_function.type set to 'function_calling'."
            )
            raise ValueError(msg)
        actions = []
        for ix, item in enumerate(self._traj_data["history"]):
            if item["role"] != "assistant":
                continue
            action = {"message": item["content"]}
            if use_function_calling:
                assert "tool_calls" in item and item["tool_calls"] is not None, (
                    f"Config is set to use `function_calling` but trajectory item {ix} is missing a tool call "
                    f"or has tool_calls set to None"
                )
                action["tool_calls"] = item["tool_calls"]
            actions.append(action)
        if len(actions) == 0:
            msg = "No actions found in trajectory"
            raise ValueError(msg)
        self._replay_action_trajs_path.write_text(json.dumps({self.instance_id: actions}))

    def _get_env(self) -> SWEEnv:
        return SWEEnv(
            deployment=self.deployment,
            repo=self.config.env.repo,
            post_startup_commands=[],
        )

    def _get_agent(self) -> DefaultAgent:
        agent = DefaultAgent.from_config(self.config.agent)
        agent._catch_errors = self._catch_errors
        agent._always_require_zero_exit_code = self._require_zero_exit_code
        return agent

    def _get_run_single(self) -> RunSingle:
        return RunSingle(
            self._get_env(),
            self._get_agent(),
            problem_statement=self.config.problem_statement,
            output_dir=Path(self.output_dir),
        )

    def main(self):
        self._create_actions_file()
        run_single = self._get_run_single()
        run_single.agent.replay_config = RunSingleConfig(
            agent=self.config.agent,
            problem_statement=run_single.problem_statement,
            env=self.config.env,
        )
        run_single.run()


def run_from_config(config: RunReplayConfig):
    RunReplay.from_config(config).main()


def run_from_cli(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    help_text = (  # type: ignore
        __doc__ + "\n[cyan][bold]=== ALL THE OPTIONS ===[/bold][/cyan]\n\n" + ConfigHelper().get_help(RunReplayConfig)
    )
    run_from_config(BasicCLI(RunReplayConfig, help_text=help_text, default_settings=False).get_config(args))  # type: ignore


if __name__ == "__main__":
    run_from_cli()
