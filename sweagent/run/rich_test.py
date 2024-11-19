import logging
import time
from concurrent.futures import ThreadPoolExecutor
from random import random
from threading import Lock

from rich.console import Group
from rich.live import Live
from rich.logging import RichHandler
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

logging.basicConfig(level="NOTSET", handlers=[RichHandler(level="NOTSET")])
logger = logging.getLogger("rich")

# Lock for thread-safe progress updates
progress_lock = Lock()


class RunBatch:
    def __init__(self):
        self.tasks = list(range(10))  # Reduced to 10 tasks for example clarity
        self._main_progress_bar: Progress | None = None
        self._task_progress_bar: Progress | None = None
        self._spinner_tasks: dict[TaskID, TaskID] = {}

    def do_task(self, task_id: TaskID):
        assert self._main_progress_bar is not None
        assert self._task_progress_bar is not None

        # Create a spinner for this task
        with progress_lock:
            spinner_task_id = self._task_progress_bar.add_task(f"Task {task_id}", total=None)

        logger.info("Starting task %d", task_id)
        # Startup
        time.sleep(random() * 4.5)
        # Work
        with progress_lock:
            self._task_progress_bar.update(spinner_task_id, description=f"Task {task_id} (working)")
        time.sleep(random() * 4.5 + 2)
        logger.info("Finished task %d", task_id)

        # Remove spinner and update main progress
        with progress_lock:
            self._task_progress_bar.remove_task(spinner_task_id)
            self._main_progress_bar.update(TaskID(0), advance=1)

    def main(self):
        # Custom progress columns
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

        group = Group(self._main_progress_bar, self._task_progress_bar)

        with Live(group):
            # Add main progress bar
            self._main_task_id = self._main_progress_bar.add_task("[cyan]Overall Progress", total=len(self.tasks))

            # Create thread pool and run tasks
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all tasks
                futures = [executor.submit(self.do_task, task_id) for task_id in self.tasks]

                # Wait for all tasks to complete
                for future in futures:
                    future.result()


if __name__ == "__main__":
    run_batch = RunBatch()
    run_batch.main()
