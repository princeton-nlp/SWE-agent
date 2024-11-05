"""
Run on a batch of instances/issues. For example run on all of SWE-bench.
"""

import json
import sys
import traceback
from pathlib import Path
from typing import Self

from pydantic import Field
from pydantic_settings import BaseSettings

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.environment.swe_env import SWEEnv
from sweagent.run.batch_instances import BatchInstance, BatchInstanceSourceConfig
from sweagent.run.common import BasicCLI, save_predictions
from sweagent.run.hooks.abstract import CombinedRunHooks, RunHook
from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
from sweagent.utils.log import get_logger


class RunBatchConfig(BaseSettings, cli_implicit_flags=True):
    instances: BatchInstanceSourceConfig = Field(union_mode="left_to_right")
    agent: AgentConfig = AgentConfig()
    traj_dir: Path = Path(".")
    raise_exceptions: bool = False
    redo_existing: bool = False


class _BreakLoop(Exception):
    """Used for internal control flow"""


class RunBatch:
    def __init__(
        self,
        instances: list[BatchInstance],
        agent: Agent,
        *,
        traj_dir: Path = Path("."),
        hooks: list[RunHook] | None = None,
        raise_exceptions: bool = False,
        redo_existing: bool = False,
    ):
        """Note: When initializing this class, make sure to add the hooks that are required by your actions.
        See `from_config` for an example.

        Args:
            hooks: If not specified, the default hooks will be used.
        """
        self.logger = get_logger("Run", emoji="🏃")
        self.instances = instances
        self.agent = agent
        self.traj_dir = traj_dir
        self._hooks = []
        self._raise_exceptions = raise_exceptions
        self._chooks = CombinedRunHooks()
        self._redo_existing = redo_existing
        for hook in hooks or [SaveApplyPatchHook()]:
            self.add_hook(hook)

    @classmethod
    def from_config(cls, config: RunBatchConfig) -> Self:
        logger = get_logger("RunBatch", emoji="🏃")
        logger.debug("Loading instances from %s", f"{config.instances!r}")
        instances = config.instances.get_instance_configs()
        logger.info("Loaded %d instances", len(instances))
        if not instances:
            msg = (
                "No instances to run. You might want to check your instance_filter "
                "(if supported by your instance source)"
            )
            raise ValueError(msg)
        logger.debug("The first instance is %s", f"{instances[0]!r}")
        return cls(
            instances=instances,
            agent=Agent("main", config.agent),
            traj_dir=config.traj_dir,
            raise_exceptions=config.raise_exceptions,
        )

    def add_hook(self, hook: RunHook) -> None:
        hook.on_init(run=self)
        self._hooks.append(hook)

    def main(self):
        self._chooks.on_start()
        for instance in self.instances:
            try:
                self.run_instance(instance)
            except _BreakLoop:
                self.logger.info("Stopping loop over instances")
                break
        self.logger.info("Done")
        self._chooks.on_end()

    def run_instance(self, instance: BatchInstance):
        # Either catch and silence exception, or raise _BreakLoop to stop the loop
        # over the instances
        try:
            self._run_instance(instance)
        except KeyboardInterrupt:
            raise _BreakLoop
        except SystemExit:
            self.logger.critical("❌ Exiting because SystemExit was called")
            raise _BreakLoop
        except Exception as e:
            self.logger.error(traceback.format_exc())
            if self._raise_exceptions:
                raise _BreakLoop
            self.logger.warning(f"❌ Failed on {instance.problem_statement.id}: {e}")

    def _run_instance(self, instance: BatchInstance):
        if self.should_skip(instance):
            return
        self.logger.info("Starting to run on instance %s", instance.problem_statement.id)
        self.logger.info("Starting environment")
        env = SWEEnv.from_config(instance.env)
        env.start()
        self.logger.info("Resetting environment")
        env.reset()
        self.logger.info("Running agent")
        self._chooks.on_instance_start(index=0, env=env, problem_statement=instance.problem_statement)
        result = self.agent.run(
            problem_statement=instance.problem_statement,
            env=env,
            traj_dir=Path(self.traj_dir),
        )
        self._chooks.on_instance_completed(result=result)
        save_predictions(self.traj_dir, instance.problem_statement.id, result)

    def should_skip(self, instance: BatchInstance) -> bool:
        """Check if we should skip this instance"""
        if self._redo_existing:
            return False

        # Check if there's an existing trajectory for this instance
        log_path = self.traj_dir / (instance.problem_statement.id + ".traj")
        if not log_path.exists():
            return False

        content = log_path.read_text()
        if not content.strip():
            self.logger.warning("Found empty trajectory: %s. Removing.", log_path)
            log_path.unlink()
            return False

        data = json.loads(content)
        # If the trajectory has no exit status, it's incomplete and we will redo it
        exit_status = data["info"].get("exit_status", None)
        if exit_status == "early_exit" or exit_status is None:
            self.logger.warning(f"Found existing trajectory with no exit status: {log_path}. Removing.")
            log_path.unlink()
            return False

        self.logger.info(f"⏭️ Skipping existing trajectory: {log_path}")
        return True


def run_from_config(args: RunBatchConfig):
    RunBatch.from_config(args).main()


def run_from_cli(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    run_from_config(BasicCLI(RunBatchConfig).get_args(args))  # type: ignore


if __name__ == "__main__":
    run_from_cli()
