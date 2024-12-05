import shutil
import subprocess
import sys
from pathlib import Path
from threading import Lock
from time import time

from sweagent.run.hooks.abstract import RunHook
from sweagent.run.merge_predictions import merge_predictions
from sweagent.types import AgentRunResult
from sweagent.utils.log import get_logger


class SweBenchEvaluate(RunHook):
    _SUBSET_MAP = {"lite": "swe-bench_lite"}

    def __init__(self, output_dir: Path, subset: str, split: str, continuous_submission_every: int = 0) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.subset = subset
        self.split = split
        self.continuous_submission_every = continuous_submission_every
        self.logger = get_logger("SB-evaluate", emoji="😬")
        self.merge_lock = Lock()
        self.last_evaluation_time = time()
        self.evaluation_interval = continuous_submission_every

    def _get_sb_call(self, preds_path: Path, prefix: str = "", overwrite: bool = False) -> list[str]:
        args = [
            "sb-cli",
            "submit",
            self._SUBSET_MAP[self.subset],
            self.split,
            "--predictions_path",
            str(preds_path),
            "--run_id",
            self.output_dir.name,
            "--output_dir",
            str(self.output_dir / f"{prefix}sb-cli-reports"),
        ]
        if overwrite:
            args.append("--overwrite")
        return args

    def on_instance_completed(self, *, result: AgentRunResult):
        if self.evaluation_interval == 0:
            return

        current_time = time()
        if current_time - self.last_evaluation_time < self.evaluation_interval:
            return

        with self.merge_lock:
            merge_predictions([self.output_dir], self.output_dir / "tmppreds.json")
            self.last_evaluation_time = current_time

        subprocess.Popen(
            self._get_sb_call(preds_path=self.output_dir / "tmppreds.json", prefix="tmp-", overwrite=True),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def on_end(self) -> None:
        self.logger.info("Submitting results to SWE-Bench")
        try:
            subprocess.run(
                self._get_sb_call(preds_path=self.output_dir / "preds.json"),
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to submit results to SweBench eval: %s", e)
        else:
            # remove temporary predictions if they exist
            if (self.output_dir / "tmppreds.json").exists():
                (self.output_dir / "tmppreds.json").unlink()
            if (self.output_dir / "tmp-sb-cli-reports").exists():
                shutil.rmtree(self.output_dir / "tmp-sb-cli-reports")
