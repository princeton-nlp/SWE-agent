"""Run on a single instance taken from github or similar."""

import json
import sys
import tempfile
from getpass import getuser
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings
from swerex.deployment.abstract import AbstractDeployment
from swerex.deployment.config import DeploymentConfig, get_deployment
from typing_extensions import Self

from sweagent.agent.agents import Agent
from sweagent.agent.models import ReplayModelConfig
from sweagent.environment.config.problem_statement import EmptyProblemStatement
from sweagent.environment.swe_env import SWEEnv
from sweagent.run.common import BasicCLI
from sweagent.run.run_single import RunSingle, RunSingleConfig
from sweagent.utils.config import load_environment_variables
from sweagent.utils.log import get_logger


class RunReplayConfig(BaseSettings):
    traj_path: Path
    deployment: DeploymentConfig | None = None
    """Override the deployment in the trajectory."""
    output_dir: Path = Path("DEFAULT")
    env_var_path: Path | None = None
    """Path to a .env file to load environment variables from."""

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
        _catch_errors: bool = False,
        _require_zero_exit_code: bool = False,
    ):
        self.traj_path = traj_path
        self.output_dir = output_dir
        self._replay_action_trajs_path = Path(tempfile.NamedTemporaryFile(suffix=".json").name)
        self.logger = get_logger("swea-run", emoji="🏃")
        self._catch_errors = _catch_errors
        self._require_zero_exit_code = _require_zero_exit_code

        if traj_path.suffix == ".yaml":
            self._traj_data = yaml.safe_load(traj_path.read_text())
        else:
            self._traj_data = json.loads(traj_path.read_text())
        self.config = self._get_config_from_agent(self._traj_data)

        if deployment is None:
            self.deployment = get_deployment(self.config.env.deployment)
        else:
            self.deployment = deployment

    def _get_config_from_agent(self, traj_data):
        try:
            config = RunSingleConfig.model_validate(self._traj_data["replay_config"])
        except KeyError:
            msg = "Replay config not found in trajectory. Are you running on an old trajectory?"
            raise ValueError(msg)
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

    def _get_agent(self) -> Agent:
        agent = Agent.from_config(self.config.agent)
        agent._catch_errors = self._catch_errors
        agent._always_require_zero_exit_code = self._require_zero_exit_code
        return agent

    def _get_run_single(self) -> RunSingle:
        return RunSingle(
            self._get_env(),
            self._get_agent(),
            problem_statement=EmptyProblemStatement(),
            output_dir=Path(self.output_dir),
        )

    def main(self):
        self._create_actions_file()
        run_single = self._get_run_single()
        run_single.run()


def run_from_config(config: RunReplayConfig):
    RunReplay.from_config(config).main()


def run_from_cli(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    run_from_config(BasicCLI(RunReplayConfig, default_settings=False).get_config(args))  # type: ignore


if __name__ == "__main__":
    run_from_cli()
