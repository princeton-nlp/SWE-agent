"""Run on a single instance taken from github or similar."""

import json
import sys
import tempfile
from getpass import getpass
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings
from swerex.deployment.abstract import AbstractDeployment
from swerex.deployment.config import DeploymentConfig, DockerDeploymentConfig

from sweagent import CONFIG_DIR
from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import ReplayModelConfig
from sweagent.environment.config.problem_statement import EmptyProblemStatement
from sweagent.environment.config.repo import RepoConfig
from sweagent.environment.swe_env import SWEEnv
from sweagent.run.common import BasicCLI
from sweagent.run.run_single import RunSingle
from sweagent.utils.config import load_environment_variables
from sweagent.utils.log import get_logger


class RunReplayConfig(BaseSettings):
    traj_path: Path
    config_path: Path = CONFIG_DIR / "default.yaml"
    deployment: DeploymentConfig = Field(default_factory=DockerDeploymentConfig)
    repo: RepoConfig | None = None
    output_dir: Path = Path("DEFAULT")
    env_var_path: Path | None = None
    """Path to a .env file to load environment variables from."""

    def model_post_init(self, __context: Any) -> None:
        if self.output_dir == Path("DEFAULT"):
            user_id = getpass.getuser()
            self.output_dir = (
                Path.cwd() / "trajectories" / user_id / f"{self.config_path.name}__replay___{self.traj_path.stem}"
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)


class RunReplay:
    def __init__(
        self,
        *,
        traj_path: Path,
        config_path: Path,
        deployment: AbstractDeployment,
        repo: RepoConfig | None,
        output_dir: Path,
        _catch_errors: bool = False,
        _require_zero_exit_code: bool = False,
    ):
        self.traj_path = traj_path
        self.config_path = config_path
        self.deployment = deployment
        self.repo = repo
        self.output_dir = output_dir
        self._replay_action_trajs_path = Path(tempfile.NamedTemporaryFile(suffix=".json").name)
        self.logger = get_logger("RunReplay", emoji="🏃")
        self._catch_errors = _catch_errors
        self._require_zero_exit_code = _require_zero_exit_code

    @property
    def instance_id(self) -> str:
        return Path(self.traj_path).stem

    @classmethod
    def from_config(cls, config: RunReplayConfig, **kwargs) -> Self:
        load_environment_variables(config.env_var_path)
        return cls(
            traj_path=config.traj_path,
            config_path=config.config_path,
            deployment=config.deployment.get_deployment(),
            repo=config.repo,
            output_dir=config.output_dir,
            **kwargs,
        )

    def _create_actions_file(self) -> None:
        traj_path = Path(self.traj_path)
        traj_data = json.loads(traj_path.read_text())
        actions = [x["content"] for x in traj_data["history"] if x["role"] == "assistant"]
        self._replay_action_trajs_path.write_text(json.dumps({self.instance_id: actions}))

    def _get_env(self) -> SWEEnv:
        return SWEEnv(
            deployment=self.deployment,
            repo=self.repo,
            startup_commands=[],
        )

    def _get_agent(self) -> Agent:
        _agent_config = yaml.safe_load(Path(self.config_path).read_text())["agent"]
        _agent_config["model"] = ReplayModelConfig(replay_path=self._replay_action_trajs_path).model_dump()
        agent_config = AgentConfig(**_agent_config)
        agent = Agent.from_config(agent_config)
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


def run_from_config(args: RunReplayConfig):
    RunReplay.from_config(args).main()


def run_from_cli(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    run_from_config(BasicCLI(RunReplayConfig, default_settings=False).get_args(args))  # type: ignore


if __name__ == "__main__":
    run_from_cli()
