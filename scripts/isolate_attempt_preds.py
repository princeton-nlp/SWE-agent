#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sweagent.utils.log import get_logger

logger = get_logger("splitter")


class TrajSplitter:
    def __init__(self, results_dir: Path):
        self._results_dir = results_dir

    def _get_trajs(self) -> list[Path]:
        res = list(self._results_dir.glob("*.traj"))
        logger.debug(f"Found {len(res)} trajectories in {self._results_dir}")
        return res

    def _get_attempts(self, results: dict) -> dict:
        return results["attempts"]

    def _get_pred_from_attempt(self, attempt: dict) -> str:
        try:
            pred = attempt["info"]["submission"]
        except KeyError:
            return ""
        if pred is None:
            return ""
        return pred

    def _get_instance_id(self, traj_path: Path) -> str:
        return traj_path.stem

    def _get_experiment_id(self, results_dir: Path) -> str:
        return results_dir.stem

    def _get_preds_path(self, i_attempt: int) -> Path:
        return self._results_dir / "by_attempt" / str(i_attempt) / "preds.jsonl"

    def _save_preds(self, *, i_attempt: int, instance_id: str, experiment_id: str, pred: str) -> None:
        out_path = self._get_preds_path(i_attempt)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.touch(exist_ok=True)
        with out_path.open("a") as f:
            f.write(
                json.dumps({"model_name_or_path": experiment_id, "instance_id": instance_id, "model_patch": pred})
                + "\n"
            )

    def _remove_existing_preds(self) -> None:
        existing_preds = list(self._results_dir.glob("by_attempt/*/preds.jsonl"))
        for pred_path in existing_preds:
            pred_path.unlink()

    def split(self) -> None:
        i_attempts = 0
        eid = self._get_experiment_id(self._results_dir)
        self._remove_existing_preds()
        for traj in self._get_trajs():
            data = json.loads(traj.read_text())
            attempts = self._get_attempts(data)
            for i_attempt, attempt in enumerate(attempts):
                i_attempts += 1
                iid = self._get_instance_id(traj)
                pred = self._get_pred_from_attempt(attempt)
                if not pred:
                    logger.warning("No prediction for instance %s attempt %d", iid, i_attempt)
                self._save_preds(
                    i_attempt=i_attempt,
                    instance_id=iid,
                    experiment_id=eid,
                    pred=pred,
                )
                attempt_traj_path = self._get_preds_path(i_attempt).parent / f"{iid}.traj"
                attempt_traj_path.write_text(json.dumps(attempt, indent=2))
        logger.info("Wrote a total of %d predictions", i_attempts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results_dir", type=Path)
    args = parser.parse_args()
    splitter = TrajSplitter(args.results_dir)
    splitter.split()
