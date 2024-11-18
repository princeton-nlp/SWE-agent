import collections
from threading import Lock

from rich.console import Group
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
from rich.table import Table


class RunBatchProgressManager:
    def __init__(
        self,
        num_instances: int,
    ):
        self._spinner_tasks: dict[str, TaskID] = {}
        self._lock = Lock()
        self.exit_status_histogram = collections.defaultdict(int)
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
            TextColumn("{task.fields[instance_id]}: "),
            TextColumn("{task.fields[status]}"),
            TimeElapsedColumn(),
        )
        self._main_progress_bar.add_task("[cyan]Overall Progress", total=num_instances)

        self.render_group = Group(Table(), self._main_progress_bar, self._task_progress_bar)

    def update_exit_status_table(self):
        t = Table()
        t.add_column("Exit Status")
        t.add_column("Count")
        t.show_header = False
        with self._lock:
            t.show_header = True
            # self._exit_status_table.rows.clear()
            for status, count in self.exit_status_histogram.items():
                t.add_row(status, str(count))
        assert self.render_group is not None
        self.render_group.renderables[0] = t

    def update_task_progress(self, instance_id: str, message: str):
        assert self._task_progress_bar is not None
        assert self._main_progress_bar is not None
        with self._lock:
            self._task_progress_bar.update(self._spinner_tasks[instance_id], status=message, instance_id=instance_id)

    def on_instance_start(self, instance_id: str):
        with self._lock:
            self._spinner_tasks[instance_id] = self._task_progress_bar.add_task(
                description=f"Task {instance_id}",
                status="Task initialized",
                total=None,
                instance_id=instance_id,
            )

    def on_instance_end(self, instance_id: str, exit_status: str):
        self.exit_status_histogram[exit_status] += 1
        with self._lock:
            self._task_progress_bar.remove_task(self._spinner_tasks[instance_id])
            self._main_progress_bar.update(TaskID(0), advance=1)
        self.update_exit_status_table()

    def on_uncaught_exception(self, instance_id: str, exception: Exception):
        with self._lock:
            self.exit_status_histogram[f"Uncaught {type(exception).__name__}"] += 1
        self.update_exit_status_table()

    def on_instance_skipped(self, instance_id: str):
        with self._lock:
            self.exit_status_histogram["skipped"] += 1
        self.update_exit_status_table()
