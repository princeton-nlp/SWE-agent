import subprocess
from pathlib import Path

from sweagent.run.hooks.abstract import RunHook


class SweBenchEvaluate(RunHook):
    _SUBSET_MAP = {"lite": "swe-bench_lite"}

    def __init__(self, output_dir: Path, subset: str, split: str) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.subset = subset
        self.split = split

    def on_end(self) -> None:
        subprocess.run(["sb-cli", "submit", self._SUBSET_MAP[self.subset], self.split, self.output_dir.name])
