from __future__ import annotations

import argparse
import json
import os
import traceback
from collections import Counter

from rich import print
from swebench import (
    KEY_INSTANCE_ID,
    KEY_MODEL,
    KEY_PREDICTION,
    get_eval_refs,
    get_eval_report,
    get_logs_eval,
    get_model_report,
    get_resolution_status,
    run_evaluation,
)
from swebench.harness.constants import (
    INSTALL_FAIL,
)
from unidiff import PatchSet


def main(
    predictions_path,
    log_dir,
    swe_bench_tasks,
    testbed,
    skip_existing,
    timeout,
    verbose,
    conda_link,
    log_suffix,
    num_processes,
):
    # Check if paths exist
    if not os.path.exists(predictions_path):
        msg = f"Predictions path {predictions_path} does not exist"
        raise FileNotFoundError(msg)
    eval_refs = get_eval_refs(swe_bench_tasks)
    for k, v in eval_refs.items():
        eval_refs[k] = {key: v[key] for key in [KEY_INSTANCE_ID, "FAIL_TO_PASS", "PASS_TO_PASS"]}

    # Change model_name_or_patch field to directory name for all predictions
    directory = os.path.dirname(predictions_path)
    directory_name = directory.rsplit("/", 1)[-1]
    pred_path_orig = predictions_path
    pred_path_temp = predictions_path.replace(".jsonl", "_filtered.jsonl")

    pred_total, pred_will_eval = 0, 0
    with open(pred_path_temp, "w") as f:
        for l in open(pred_path_orig).readlines():
            pred_total += 1
            p = json.loads(l)
            # Exclude predictions w/ empty strings
            if p[KEY_PREDICTION] is not None and p[KEY_PREDICTION].strip() != "":
                p[KEY_MODEL] = directory_name
                json.dump(p, f)
                f.write("\n")
                pred_will_eval += 1
    print(
        f"Found {pred_total} total predictions, will evaluate {pred_will_eval} ({pred_total-pred_will_eval} are empty)"
    )

    # Run evaluation
    predictions_path = pred_path_temp
    try:
        print("🏃 Beginning evaluation...")
        run_evaluation(
            predictions_path=predictions_path,
            log_dir=log_dir,
            swe_bench_tasks=swe_bench_tasks,
            testbed=testbed,
            skip_existing=skip_existing,
            timeout=timeout,
            verbose=verbose,
            conda_link=conda_link,
            log_suffix=log_suffix,
            num_processes=num_processes,
        )
        print("✅ Finished evaluation")
    except Exception as e:
        print(f"❌ Evaluation failed: {e}\n{traceback.format_exc()}")
    print("==================================")
    os.remove(pred_path_temp)

    # Get predictions, define log_dir
    predictions = [json.loads(l) for l in open(pred_path_orig).readlines()]
    log_dir = os.path.join(log_dir, directory_name)
    print(f"Log directory for evaluation run: {log_dir}")

    # Iterate through predictions
    scorecards = []
    for p in predictions:
        scorecard = {KEY_INSTANCE_ID: p[KEY_INSTANCE_ID], "statuses": [], "stats": {}}

        # Add trajectory statistics if traj_path exists
        traj_path = os.path.join(directory, f"{p[KEY_INSTANCE_ID]}.traj")
        if os.path.exists(traj_path):
            traj_data = json.load(open(traj_path))
            scorecard["stats"]["traj_num_steps"] = len(traj_data["trajectory"])
            scorecard["stats"]["traj_action_dist"] = dict(
                Counter(
                    [
                        entry["action"].strip().split()[0]
                        if entry["role"] == "assistant" and "action" in entry and len(entry["action"]) > 0
                        else None
                        for entry in traj_data["history"]
                    ]
                )
            )
            scorecard["exit_status"] = traj_data["info"]["exit_status"] if "exit_status" in traj_data["info"] else "n/a"

        # Check that a prediction was generated
        if p[KEY_PREDICTION] is None or p[KEY_PREDICTION].strip() == "":
            scorecard["statuses"].append("not_generated")
            scorecards.append(scorecard)
            continue
        scorecard["statuses"].append("generated")

        # Get log file
        log_path = os.path.join(log_dir, f"{p[KEY_INSTANCE_ID]}.{directory_name}.eval.log")
        if not os.path.exists(log_path):
            scorecard["statuses"].append("build_failure")
            scorecards.append(scorecard)
            continue

        # Get evaluation logs
        eval_sm, found = get_logs_eval(log_path)

        # Check that the prediction generated
        if not found:
            scorecards.append(scorecard)
            continue
        scorecard["statuses"].append("applied")

        with open(log_path) as f:
            log_contents = f.read()
            if INSTALL_FAIL in log_contents:
                scorecard["statuses"].append("install_fail")

        # Get resolution status
        report = get_eval_report(eval_sm, eval_refs[p[KEY_INSTANCE_ID]])
        scorecard["test_results"] = {
            "failure": {
                "FAIL_TO_PASS": report["FAIL_TO_PASS"]["failure"],
                "PASS_TO_PASS": report["PASS_TO_PASS"]["failure"],
            },
            "success": {
                "FAIL_TO_PASS": report["FAIL_TO_PASS"]["success"],
                "PASS_TO_PASS": report["PASS_TO_PASS"]["success"],
            },
        }
        resolution_status = get_resolution_status(report)
        scorecard["statuses"].append(resolution_status)

        try:
            diff_obj = PatchSet(p[KEY_PREDICTION])
            scorecard["patch_files"] = [
                x.path for x in diff_obj.modified_files + diff_obj.added_files + diff_obj.removed_files
            ]
            scorecard["patch_lines_add"] = sum(f.added for f in diff_obj)
            scorecard["patch_lines_del"] = sum(f.removed for f in diff_obj)
        except Exception as e:
            print(f"[{p[KEY_INSTANCE_ID]}] Error parsing prediction diff: {e}")
            scorecard["patch_files"] = []
            scorecard["patch_lines_add"] = 0
            scorecard["patch_lines_del"] = 0
        scorecards.append(scorecard)

    # Save to summary, scorecard json
    path_scorecards = os.path.join(directory, "scorecards.json")
    with open(path_scorecards, "w") as f:
        json.dump(scorecards, fp=f, indent=2)
    print(f"- Wrote per-instance scorecards to {path_scorecards}")

    # Get results and write to file
    print("Reference Report:")
    report = get_model_report(directory_name, pred_path_orig, swe_bench_tasks, log_dir)
    for k, v in report.items():
        print(f"- {k}: {len(v)}")

    path_results = os.path.join(directory, "results.json")
    with open(path_results, "w") as f:
        json.dump(report, f, indent=2)
    print(f"- Wrote summary of run to {path_results}")


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--predictions_path",
        type=str,
        help="Path to predictions file (.jsonl)",
        required=True,
    )
    parser.add_argument("--log_dir", type=str, help="Path to log directory", required=True)
    parser.add_argument(
        "--swe_bench_tasks",
        type=str,
        help="Path to SWE-bench task instances file",
        required=True,
    )
    parser.add_argument("--testbed", type=str, help="Path to testbed directory", required=True)
    parser.add_argument("--skip_existing", action="store_true", help="(Optional) Skip existing logs")
    parser.add_argument(
        "--timeout",
        type=int,
        help="(Optional) Timeout in seconds (default: 900)",
        default=900,
    )
    parser.add_argument("--verbose", action="store_true", help="(Optional) Verbose mode")
    parser.add_argument("--conda_link", default=None, type=str, help="(Optional) URL to conda installation to use")
    parser.add_argument("--log_suffix", default=None, type=str, help="(Optional) Log suffix")
    parser.add_argument("--num_processes", default=-1, type=int, help="Num processes")
    args = parser.parse_args()
    main(**vars(args))
