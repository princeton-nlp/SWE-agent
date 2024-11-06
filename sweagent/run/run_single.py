"""Run on a single instance taken from github or similar."""

import sys
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.environment.config.problem_statement import (
    EmptyProblemStatement,
    ProblemStatement,
    ProblemStatementConfig,
)
from sweagent.environment.swe_env import EnvironmentConfig, SWEEnv
from sweagent.run.common import BasicCLI, save_predictions
from sweagent.run.hooks.abstract import CombinedRunHooks, RunHook
from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
from sweagent.run.hooks.open_pr import OpenPRConfig, OpenPRHook
from sweagent.utils.log import get_logger


class RunSingleActionConfig(BaseModel, cli_implicit_flags=True):
    """Run real-life actions (opening PRs, etc.) if we can solve the issue."""

    # Open a PR with the patch if we can solve the issue
    open_pr: bool = False
    pr_config: OpenPRConfig = Field(default_factory=OpenPRConfig)
    # When working with local repository: Apply patch
    apply_patch_locally: bool = False


class RunSingleConfig(BaseSettings, cli_implicit_flags=True):
    env: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    problem_statement: ProblemStatementConfig = Field(default_factory=EmptyProblemStatement)
    traj_dir: Path = Path(".")
    actions: RunSingleActionConfig = Field(default_factory=RunSingleActionConfig)

    print_config: bool = False
    """Print config at the beginning of the run."""

    # pydantic config
    model_config = ConfigDict(extra="forbid")  # type: ignore


class RunSingle:
    def __init__(
        self,
        env: SWEEnv,
        agent: Agent,
        problem_statement: ProblemStatement | ProblemStatementConfig,
        *,
        traj_dir: Path = Path("."),
        hooks: list[RunHook] | None = None,
        actions: RunSingleActionConfig | None = None,
    ):
        """Note: When initializing this class, make sure to add the hooks that are required by your actions.
        See `from_config` for an example.
        """
        self.logger = get_logger("Run", emoji="🏃")
        self.env = env
        self.agent = agent
        self.traj_dir = traj_dir
        self._hooks = []
        if actions is not None:
            actions = RunSingleActionConfig()
        self.actions = actions
        self._chooks = CombinedRunHooks()
        self.problem_statement = problem_statement
        for hook in hooks or []:
            self.add_hook(hook)

    @property
    def hooks(self) -> list[RunHook]:
        return self._chooks.hooks

    @classmethod
    def from_config(cls, config: RunSingleConfig) -> Self:
        logger = get_logger("Run", emoji="🏃")
        if config.print_config:
            config_str = yaml.dump(config.model_dump())
            logger.info(f"Config:\n {config_str}")
        self = cls(
            env=SWEEnv.from_config(config.env),
            agent=Agent("main", config.agent),
            problem_statement=config.problem_statement,
            traj_dir=config.traj_dir,
            actions=config.actions,
        )
        self.add_hook(SaveApplyPatchHook(apply_patch_locally=config.actions.apply_patch_locally))
        if config.actions.open_pr:
            self.logger.debug("Adding OpenPRHook")
            self.add_hook(OpenPRHook(config.actions.pr_config))
        return self

    def add_hook(self, hook: RunHook) -> None:
        hook.on_init(run=self)
        self._chooks.add_hook(hook)

    def run(self):
        self._chooks.on_start()
        self.logger.info("Starting environment")
        self.env.start()
        self.logger.info("Resetting environment")
        self.env.reset()
        self.logger.info("Running agent")
        self._chooks.on_instance_start(index=0, env=self.env, problem_statement=self.problem_statement)
        result = self.agent.run(
            problem_statement=self.problem_statement,
            env=self.env,
            traj_dir=Path(self.traj_dir),
        )
        self._chooks.on_instance_completed(result=result)
        self.logger.info("Done")
        self._chooks.on_end()
        save_predictions(self.traj_dir, self.problem_statement.id, result)


def run_from_config(args: RunSingleConfig):
    RunSingle.from_config(args).run()


def run_from_cli(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    run_from_config(BasicCLI(RunSingleConfig).get_args(args))  # type: ignore


if __name__ == "__main__":
    run_from_cli()
