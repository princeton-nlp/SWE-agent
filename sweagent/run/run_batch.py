"""Run in human mode without any complicated env setup.
This is mostly for debugging and development.
"""

from pathlib import Path
from typing import Self

from pydantic_settings import BaseSettings

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentInstanceConfig, SWEEnv
from sweagent.run._common import BasicCLI
from sweagent.run.batch_instances import InstanceSourceConfig
from sweagent.run.hooks.abstract import RunHook
from sweagent.utils.log import get_logger


class RunBatchConfig(BaseSettings):
    instances: InstanceSourceConfig
    agent: AgentConfig = AgentConfig(
        model=ModelArguments(name="human"), next_step_template="Observation: {observation}"
    )
    traj_dir: str = "."
    raise_exceptions: bool = False


class RunBatch:
    def __init__(
        self,
        instances: list[EnvironmentInstanceConfig],
        agent: Agent,
        *,
        traj_dir: str = ".",
        hooks: list[RunHook] | None = None,
    ):
        """Note: When initializing this class, make sure to add the hooks that are required by your actions.
        See `from_config` for an example.
        """
        self.logger = get_logger("🤠 Run")
        self.instances = instances
        self.agent = agent
        self.traj_dir = traj_dir
        self._hooks = []
        for hook in hooks or []:
            self.add_hook(hook)

    @property
    def hooks(self) -> list[RunHook]:
        return self._hooks

    @classmethod
    def from_config(cls, config: RunBatchConfig) -> Self:
        return cls(
            instances=config.instances.get_instance_configs(),
            agent=Agent("main", config.agent),
            traj_dir=config.traj_dir,
        )

    def add_hook(self, hook: RunHook) -> None:
        hook.on_init(run=self)
        self._hooks.append(hook)

    def _fire_hooks(self, hook_name: str, *args, **kwargs) -> None:
        for hook in self.hooks:
            getattr(hook, hook_name)(*args, **kwargs)

    def main(self):
        self._fire_hooks("on_start")
        for instance in self.instances:
            self.logger.info("Starting environment")
            env = SWEEnv.from_config(instance)
            env.start()
            self.logger.info("Resetting environment")
            observation, info = env.reset()
            self.logger.info("Running agent")
            self._fire_hooks("on_instance_start", index=0, instance=instance.model_dump())
            info, trajectory = self.agent.run(
                setup_args={"problem_statement": instance.problem_statement.get_problem_statement()},
                env=env,
                observation=observation,
                traj_dir=Path(self.traj_dir),
                return_type="info_trajectory",
            )
        self._fire_hooks("on_instance_completed", info=info, trajectory=trajectory)
        self.logger.info("Done")
        self._fire_hooks("on_end")


def main(args: RunBatchConfig):
    RunBatch.from_config(args).main()


if __name__ == "__main__":
    main(BasicCLI(RunBatchConfig).get_args())  # type: ignore
