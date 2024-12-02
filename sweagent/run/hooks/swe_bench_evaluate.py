import subprocess
from pathlib import Path

from sweagent.run.hooks.abstract import RunHook
from sweagent.utils.log import get_logger


class SweBenchEvaluate(RunHook):
    _SUBSET_MAP = {"lite": "swe-bench_lite"}

    def __init__(self, output_dir: Path, subset: str, split: str) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.subset = subset
        self.split = split
        self.logger = get_logger("SB-evaluate", emoji="😬")

    def on_end(self) -> None:
        try:
            subprocess.check_output(
                [
                    "sb-cli",
                    "submit",
                    self._SUBSET_MAP[self.subset],
                    self.split,
                    "--predictions_path",
                    self.output_dir / "preds.json",
                    "--run_id",
                    self.output_dir.name,
                ]
            )
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to submit results to SweBench eval: %s", e)
