from __future__ import annotations

import io
import subprocess
from contextlib import redirect_stdout

from run import get_args_dev, main


def get_runnable_problems(trajectory_path):
    import os

    from datasets import load_dataset

    d = load_dataset("princeton-nlp/SWE-bench_Lite")

    traj_files = []
    for root, dirs, files in os.walk(trajectory_path):
        for file in files:
            if file.endswith(".traj"):
                traj_files.append(file.split(".")[0])

    dev_question_ids = [q["instance_id"] for q in d["dev"]]
    test_question_ids = [q["instance_id"] for q in d["test"]]

    return {
        "dev": [q for q in dev_question_ids if q in traj_files],
        "test": [q for q in test_question_ids if q in traj_files],
    }


def run_swebench_evaluation(
    predictions_path_override=None,
    model_name="gpt-4o-mini",
    dataset_name="princeton-nlp/SWE-bench_Lite",
    cost_limit=0.05,
    temperature=0.00,
    top_p=0.95,
    max_workers=1,
    run_id="josh-testing",
    split="dev",
):
    if predictions_path_override is None:
        predictions_path = f"trajectories/jp/{model_name}/{dataset_name}__SWE-bench_Lite__default__t-{temperature:.2f}__p-0.95__c-{cost_limit}__install-1/all_preds.jsonl"
    else:
        predictions_path = predictions_path_override

    ids_by_split = get_runnable_problems("/".join(predictions_path.split("/")[:-1]))
    import json

    # Load all predictions
    with open(predictions_path, "r") as f:
        all_preds = [json.loads(line) for line in f]
    # Separate predictions into dev and test
    dev_preds = [pred for pred in all_preds if pred["instance_id"] in ids_by_split["dev"]]
    test_preds = [pred for pred in all_preds if pred["instance_id"] in ids_by_split["test"]]

    # Save dev predictions
    dev_preds_path = predictions_path.replace("all_preds.jsonl", "all_dev_preds.jsonl")
    with open(dev_preds_path, "w") as f:
        for pred in dev_preds:
            json.dump(pred, f)
            f.write("\n")

    # Save test predictions
    test_preds_path = predictions_path.replace("all_preds.jsonl", "all_test_preds.jsonl")
    with open(test_preds_path, "w") as f:
        for pred in test_preds:
            json.dump(pred, f)
            f.write("\n")

    # Update predictions_path to use the appropriate file based on the split
    predictions_path = dev_preds_path if split == "dev" else test_preds_path
    preds = dev_preds if split == "dev" else test_preds
    if len(preds) == 0:
        print(f"No predictions found for split {split}")
        return
    command = [
        "python",
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        dataset_name,
        "--predictions_path",
        predictions_path,
        "--max_workers",
        str(max_workers),
        "--run_id",
        run_id,
        "--split",
        split,
    ]

    # Split out data from dev/test into separate preds file and run on it

    result = subprocess.run(command, capture_output=True, text=True)
    print("STDERR:", result.stderr)
    # Parse and print the summary
    lines = result.stdout.split("\n")
    for line in lines:
        if "Report written to " in line:
            file_name = line.replace("Report written to ", "")
            with open(file_name, "r") as f:
                summary = json.load(f)
            failed_ids = summary["unresolved_ids"]
            success_ids = summary["resolved_ids"]
            from colorama import Fore, Style, init

            init(autoreset=True)

            print("\nResults:")
            for id in success_ids + failed_ids:
                color = Fore.LIGHTGREEN_EX if id in success_ids else Fore.LIGHTRED_EX
                print(f"{color}• {id}{Style.RESET_ALL}")


def run_and_catch_logs(
    model_name="gpt-4o-mini", instance="marshmallow-code__marshmallow-1359", cost_limit=0.05, split="dev"
):
    output = io.StringIO()
    with redirect_stdout(output):
        main(
            get_args_dev(
                model_name=model_name, instance_to_filter_by=instance, per_instance_cost_limit=cost_limit, split=split
            )
        )

    captured_logs = output.getvalue()
    log_lines = captured_logs.splitlines()
    print(f"Captured {len(log_lines)} lines of logs")


# TODO: goal here is for us to be able to run swe-agent and then eval it with swe-bench to know correct/incorrect.
# Then, to enable us to add scoring functions that parse through the logged lines and keep track of intermediate metrics
if __name__ == "__main__":
    from datasets import load_dataset

    # TODO: seems like in my local env I'm struggling with two packages causing run fails
    # 0-2 types-pkg_resources
    # 10 Failed to build h5py

    run_agent = True
    evaluate_agent = True
    d = load_dataset("princeton-nlp/SWE-bench_Lite")
    runnable_problems_by_split = get_runnable_problems(
        "trajectories/jp/gpt-4o-mini__SWE-bench_Lite__default__t-0.00__p-0.95__c-0.05__install-1"
    )
    print({k: len(v) for k, v in runnable_problems_by_split.items()})

    split = "test"
    if run_agent:
        for question_index in range(0, 10):
            print("Running agent for question index: ", question_index)
            print(d[split][question_index]["instance_id"])
            run_and_catch_logs(instance=d[split][question_index]["instance_id"], cost_limit=0.05, split=split)
    if evaluate_agent:
        import time

        t0 = time.time()
        splits = ["dev", "test"]
        for split in splits:
            print("Running evaluation for split: ", split)
            run_swebench_evaluation(
                predictions_path_override=None,#"trajectories/jp/gpt-4o-mini__SWE-bench_Lite__default__t-0.00__p-0.95__c-0.05__install-1/all_preds.jsonl"
                model_name="gpt-4o-mini",
                dataset_name="princeton-nlp/SWE-bench_Lite",
                cost_limit=0.05,
                temperature=0.00,
                top_p=0.95,
                run_id="test",
                split=split,
                max_workers=2,
            )
        print("Time taken: ", time.time() - t0)
        # 9.560726881027222 - cached 14/0
        #
    # Successes so far
    # gpt-4o-mini
    # • pvlib__pvlib-python-1072
    # • pydicom__pydicom-1694

    # TODO
    # get successes with sonnet and mini
    # try out L3.1-70b with 128k context to see where it stacks up
