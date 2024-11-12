"""
Run on a batch of instances/issues. For example run on all of SWE-bench.
"""

import getpass
import json
import sys
import traceback
from pathlib import Path
from typing import Self

from pydantic_settings import BaseSettings

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.environment.swe_env import SWEEnv
from sweagent.run.batch_instances import BatchInstance, BatchInstanceSourceConfig
from sweagent.run.common import BasicCLI, save_predictions
from sweagent.run.hooks.abstract import CombinedRunHooks, RunHook
from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
from sweagent.utils.config import load_environment_variables
from sweagent.utils.log import get_logger


class RunBatchConfig(BaseSettings, cli_implicit_flags=True):
    instances: BatchInstanceSourceConfig
    agent: AgentConfig
    output_dir: Path = Path("DEFAULT")
    raise_exceptions: bool = False
    redo_existing: bool = False
    env_var_path: Path | None = None
    """Path to a .env file to load environment variables from."""

    def set_default_output_dir(self) -> None:
        # Needs to be called explicitly, because self._config_files will be setup
        # post-init.
        if self.output_dir == Path("DEFAULT"):
            user_id = getpass.getuser()
            source_id = self.instances.id
            model_id = self.agent.model.id
            config_file = getattr(self, "_config_files", ["no_config"])[0]
            if isinstance(config_file, Path):
                config_file = config_file.stem
            self.output_dir = Path.cwd() / "trajectories" / user_id / f"{config_file}__{model_id}___{source_id}"


class _BreakLoop(Exception):
    """Used for internal control flow"""


class RunBatch:
    def __init__(
        self,
        instances: list[BatchInstance],
        agent: Agent,
        *,
        output_dir: Path = Path("."),
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
        self.output_dir = output_dir
        self._hooks = []
        self._raise_exceptions = raise_exceptions
        self._chooks = CombinedRunHooks()
        self._redo_existing = redo_existing
        for hook in hooks or [SaveApplyPatchHook()]:
            self.add_hook(hook)

    @classmethod
    def from_config(cls, config: RunBatchConfig) -> Self:
        load_environment_variables(config.env_var_path)
        config.set_default_output_dir()
        config.output_dir.mkdir(parents=True, exist_ok=True)
        logger = get_logger("RunBatch", emoji="🏃")
        logger.debug("Loading instances from %s", f"{config.instances!r}")
        instances = config.instances.get_instance_configs()
        logger.info("Loaded %d instances", len(instances))
        if not instances:
            msg = (
                "No instances to run. Here are a few things to check:\n"
                "- With huggingface data: Check that you have the right split (test or dev)\n"
                "- Check your filter does not exclude all instances (check the info log messages)"
            )
            raise ValueError(msg)
        logger.debug("The first instance is %s", f"{instances[0]!r}")
        return cls(
            instances=instances,
            agent=Agent.from_config(config.agent),
            output_dir=config.output_dir,
            raise_exceptions=config.raise_exceptions,
        )

    def add_hook(self, hook: RunHook) -> None:
        hook.on_init(run=self)
        self._hooks.append(hook)

    def main(self):
        self._chooks.on_start()
        for i_instance, instance in enumerate(self.instances):
            self.logger.info(
                "Starting to run on instance %d/%d: %s",
                i_instance + 1,
                len(self.instances),
                instance.problem_statement.id,
            )
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
            if self._raise_exceptions:
                raise
            self.logger.critical("❌ Exiting because SystemExit was called")
            raise _BreakLoop
        except Exception as e:
            self.logger.error(traceback.format_exc())
            if self._raise_exceptions:
                raise
            self.logger.warning(f"❌ Failed on {instance.problem_statement.id}: {e}")

    def _run_instance(self, instance: BatchInstance):
        if self.should_skip(instance):
            return
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
            output_dir=Path(self.output_dir),
        )
        save_predictions(self.output_dir, instance.problem_statement.id, result)
        self._chooks.on_instance_completed(result=result)
        env.close()

    def should_skip(self, instance: BatchInstance) -> bool:
        """Check if we should skip this instance"""
        if self._redo_existing:
            return False

        # Check if there's an existing trajectory for this instance
        log_path = self.output_dir / (instance.problem_statement.id + ".traj")
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
