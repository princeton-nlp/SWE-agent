"""
Run on a batch of instances/issues. For example run on all of SWE-bench.
"""

import getpass
import json
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Self

from pydantic_settings import BaseSettings
from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

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
    num_workers: int = 1
    """Number of parallel workers to use. Default is 1 (sequential execution)."""

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
        num_workers: int = 1,
    ):
        """Note: When initializing this class, make sure to add the hooks that are required by your actions.
        See `from_config` for an example.

        Args:
            hooks: If not specified, the default hooks will be used.
            num_workers: Number of parallel workers to use. Default is 1 (sequential execution).
        """
        self.logger = get_logger("Run", emoji="🏃")
        self.instances = instances
        self.agent = agent
        self.output_dir = output_dir
        self._hooks = []
        self._raise_exceptions = raise_exceptions
        self._chooks = CombinedRunHooks()
        self._redo_existing = redo_existing
        self._num_workers = num_workers
        for hook in hooks or [SaveApplyPatchHook()]:
            self.add_hook(hook)

        self._main_progress_bar: Progress | None = None
        self._task_progress_bar: Progress | None = None
        self._spinner_tasks: dict[TaskID, TaskID] = {}
        self._progress_lock = Lock()

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
            redo_existing=config.redo_existing,
            num_workers=config.num_workers,
        )

    def add_hook(self, hook: RunHook) -> None:
        hook.on_init(run=self)
        self._hooks.append(hook)

    def main(self):
        self._chooks.on_start()

        if self._num_workers <= 1:
            # Run sequentially if num_workers is 1
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
        else:
            self._main_progress_bar = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            )
            self._task_progress_bar = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
            )
            self._main_progress_bar.add_task("[cyan]Overall Progress", total=len(self.instances))

            group = Group(self._main_progress_bar, self._task_progress_bar)

            with Live(group):
                # Run in parallel with thread pool
                with ThreadPoolExecutor(max_workers=self._num_workers) as executor:
                    # Submit all tasks
                    future_to_instance = {
                        executor.submit(self.run_instance, instance): (i, instance)
                        for i, instance in enumerate(self.instances)
                    }

                    # Process completed tasks as they finish
                    try:
                        for future in as_completed(future_to_instance):
                            i, instance = future_to_instance[future]
                            future.result()  # This will raise any exceptions from run_instance
                            self.logger.info(
                                "Completed instance %d/%d: %s",
                                i + 1,
                                len(self.instances),
                                instance.problem_statement.id,
                            )
                    except (KeyboardInterrupt, _BreakLoop):
                        self.logger.info("Received keyboard interrupt, stopping parallel execution")
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise _BreakLoop

        self.logger.info("Done")
        self._chooks.on_end()

    def run_instance(self, instance: BatchInstance):
        assert self._main_progress_bar is not None
        assert self._task_progress_bar is not None

        with self._progress_lock:
            spinner_task_id = self._task_progress_bar.add_task(f"Task {instance.problem_statement.id}", total=None)

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
            self.logger.error(f"❌ Failed on {instance.problem_statement.id}: {e}")

        with self._progress_lock:
            self._task_progress_bar.remove_task(spinner_task_id)
            self._main_progress_bar.update(TaskID(0), advance=1)

    def _run_instance(self, instance: BatchInstance):
        if self.should_skip(instance):
            return
        self.logger.info("Starting environment")
        env = SWEEnv.from_config(instance.env)
        env.start()
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
