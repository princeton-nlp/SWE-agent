from __future__ import annotations

import os
from pathlib import Path

from instances import instance_id_list

# various configurable things.  Many these will go into computing the path for
# the trajectory directory that contains all_preds.jsonl after an inference run.
model_name = "claude-sonnet-3.5"
dataset_name = "princeton-nlp/SWE-bench_Verified"
split = "test"
config = "default_with_tools"
temperature = 0
top_p = 0.95
per_instance_cost_limit_usd = 4.00

# Total cost:
# Our daily limit is roughly 50M tokens, so let's make sure that no single run hits it.
# Estimate: (40M input tokens) * ($3 / MToken).
total_cost_limit_usd = 40 * 3
install_env="install"
skip_existing = True # will cause us to not re-run inference if the predictions already exists for an instance

ROOT_DIR = os.path.join(os.path.dirname(__file__),  "..")

def trajectory_dir():
    return f"trajectories/{os.getlogin()}/{model_name}__{Path(dataset_name).stem}__{config}__t-{temperature:.2f}__p-{top_p:.2f}__c-{per_instance_cost_limit_usd:.2f}__{install_env}-1"

def run_python_cmd(cmd: str, args: dict[str, str]):
    # convert args to a string
    args_str = " ".join([f"--{k} {v}" for k, v in args.items()])
    # execute the command
    print(f"Running command: python {cmd} {args_str}")
    os.system(f"python {cmd} {args_str}")

def run_inference():
    print(f"Running inference:")
    run_python_cmd("run.py", {
        "model_name": model_name,
        "per_instance_cost_limit": per_instance_cost_limit_usd,
        "total_cost_limit": total_cost_limit_usd,
        "config_file": f"./config/{config}.yaml",
        "data_path": dataset_name,
        "split": split,
        "instance_filter": f"\"{'|'.join(instance_id_list)}\"", # make sure we quote this because it contains a | symbol which the shell will want to interpret.
        "skip_existing": skip_existing,
    })

def run_evaluation(predictions_path):
    print(f"Running evaluation:")
    run_python_cmd("-m swebench.harness.run_evaluation", {
        "run_id": "command_line_test",
        "dataset_name": dataset_name,
        "predictions_path": predictions_path,
#        "max_workers": 1,
        "split": split,
        "instance_ids": " ".join(instance_id_list),
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()

    # parse command line arguments for "--inference" and "--evaluation" (both are store_true), and a --predictions_path argument for evaluation.
    parser.add_argument("--inference", action="store_true")
    parser.add_argument("--evaluation", action="store_true")
    parser.add_argument("--predictions_path", type=str)
    args = parser.parse_args()

    # Go to root dir.
    os.chdir(ROOT_DIR)

    if args.inference:
        run_inference()

    if args.evaluation:
        predictions_path = args.predictions_path if args.predictions_path is not None else Path(trajectory_dir()) / "all_preds.jsonl"
        run_evaluation(predictions_path)
