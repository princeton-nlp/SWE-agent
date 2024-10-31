"""Run on a single instance taken from github or similar."""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentInstanceConfig, SWEEnv
from sweagent.run._common import BasicCLI
from sweagent.run.hooks.abstract import CombinedRunHooks, RunHook
from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
from sweagent.run.hooks.open_pr import OpenPRConfig, OpenPRHook
from sweagent.utils.log import get_logger


class RunSingleActionConfig(BaseModel):
    """Run real-life actions (opening PRs, etc.) if we can solve the issue."""

    # Open a PR with the patch if we can solve the issue
    open_pr: bool = False
    pr_config: OpenPRConfig = Field(default_factory=OpenPRConfig)
    # When working with local repository: Apply patch
    apply_patch_locally: bool = False


class RunSingleConfig(BaseSettings):
    env: EnvironmentInstanceConfig = Field(default_factory=EnvironmentInstanceConfig)
    agent: AgentConfig = AgentConfig(
        model=ModelArguments(name="human"), next_step_template="Observation: {observation}"
    )
    traj_dir: str = "."
    actions: RunSingleActionConfig = Field(default_factory=RunSingleActionConfig)
    # todo: implement this
    raise_exceptions: bool = True
    # todo: implement this
    print_config: bool = True


class RunSingle:
    def __init__(
        self,
        env: SWEEnv,
        agent: Agent,
        *,
        traj_dir: str = ".",
        hooks: list[RunHook] | None = None,
        actions: RunSingleActionConfig,
    ):
        """Note: When initializing this class, make sure to add the hooks that are required by your actions.
        See `from_config` for an example.
        """
        self.logger = get_logger("PlaygroundMain")
        self.env = env
        self.agent = agent
        self.traj_dir = traj_dir
        self._hooks = []
        self.actions = actions
        self._chooks = CombinedRunHooks()
        for hook in hooks or []:
            self.add_hook(hook)

    @property
    def hooks(self) -> list[RunHook]:
        return self._chooks.hooks

    @classmethod
    def from_config(cls, config: RunSingleConfig) -> Self:
        self = cls(
            env=SWEEnv.from_config(config.env),
            agent=Agent("main", config.agent),
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

    def main(self):
        self._chooks.on_start()
        self.logger.info("Starting environment")
        self.env.start()
        self.logger.info("Resetting environment")
        observation, info = self.env.reset()
        self.logger.info("Running agent")
        self._chooks.on_instance_start(index=0, env=self.env)
        info, trajectory = self.agent.run(
            setup_args={"problem_statement": self.env.problem_statement.get_problem_statement()},
            env=self.env,
            observation=observation,
            traj_dir=Path(self.traj_dir),
        )
        self._chooks.on_instance_completed(info=info, trajectory=trajectory)
        self.logger.info("Done")
        self._chooks.on_end()


def main(args: RunSingleConfig):
    RunSingle.from_config(args).main()


if __name__ == "__main__":
    main(BasicCLI(RunSingleConfig).get_args())  # type: ignore
