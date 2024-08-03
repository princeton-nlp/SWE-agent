from __future__ import annotations

import io
import subprocess
from contextlib import redirect_stdout
import re

from run import main, ScriptArguments, EnvironmentArguments, AgentArguments, ModelArguments, ActionsArguments, CONFIG_DIR
from getpass import getuser

def get_args_dev(
    model_name=None,
    instance_to_filter_by="marshmallow-code__marshmallow-1359",
    per_instance_cost_limit=0.025,
    split="dev",
) -> ScriptArguments:
    return ScriptArguments(
        suffix="",
        environment=EnvironmentArguments(
            image_name="sweagent/swe-agent:latest",
            data_path="princeton-nlp/SWE-bench_Lite",
            split=split,
            verbose=False,
            install_environment=True,
            cache_task_images=False,
        ),
        skip_existing=True,
        agent=AgentArguments(
            model=ModelArguments(
                model_name=model_name,
                total_cost_limit=0.0,
                per_instance_cost_limit=per_instance_cost_limit,
                temperature=0.0,
                top_p=0.95,
            ),
            config_file=CONFIG_DIR / "default.yaml",
        ),
        actions=ActionsArguments(open_pr=False, skip_if_commits_reference_issue=True),
        instance_filter=instance_to_filter_by,
    )


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


def compare_filename_in_patches(pred_patch, expected_patch):
    if not pred_patch or expected_patch is None:
        return 0.0
    pred_match = re.findall(r'\+\+\+ b/(.*)', pred_patch)
    if not pred_match:
        return 0.0
    
    pred_filenames = {match.lower().strip() for match in pred_match}

    expected_match = re.findall(r'\+\+\+ b/(.*)', expected_patch)
    if not expected_match:
        return 1.0
    expected_filenames = {match.lower().strip() for match in expected_match}
    if not expected_filenames:
        return 0.0
    
    matched_filenames = pred_filenames & expected_filenames
    return len(matched_filenames) / len(expected_filenames) * 100.0

def run_swebench_evaluation(
    predictions_path_override=None,
    model_name=None,
    full_dataset_name="princeton-nlp/SWE-bench_Lite",
    cost_limit=0.05,
    temperature=0.00,
    top_p=0.95,
    max_workers=1,
    run_id="josh-testing",
    split="dev",
    full_dataset=None,
):
    if predictions_path_override is None:
        dataset_name = full_dataset_name.split('/')[-1]
        predictions_path = f"trajectories/{getuser()}/{model_name}__{dataset_name}__default__t-{temperature:.2f}__p-0.95__c-{cost_limit:.2f}__install-1/all_preds.jsonl"
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
    
    milestone_1_percents = {}
    dataset = full_dataset[split]
    for pred in preds:
        instance_id = pred["instance_id"]
        filtered_dataset = dataset.filter(lambda example: example['instance_id'] == instance_id)
        expected = filtered_dataset[0]
        milestone_1_percents[instance_id] = compare_filename_in_patches(pred['model_patch'], expected['patch'])
    milestone_1_success = [id for id, percent in milestone_1_percents.items() if percent == 100]
    milestone_1_mean = sum(milestone_1_percents.values()) / len(milestone_1_percents) if milestone_1_percents else 0
    print(f'PATCHED ALL FILES: {len(milestone_1_success)}/{len(preds)}')
    print(f'MEAN FILES PATCHED: {milestone_1_mean:.2f}%')

    command = [
        "python",
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        full_dataset_name,
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
                perc = milestone_1_percents.get(id, 0)
                milestone_1_emoji = '✅' if perc == 100 else '❌'
                milestone_1 = f' (PATCHED FILES: {perc}% {milestone_1_emoji})'
                print(f"{color}• {id}{milestone_1}{Style.RESET_ALL}")


def run_and_catch_logs(
    model_name=None, instance="marshmallow-code__marshmallow-1359", cost_limit=0.05, split="dev"
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
    d = load_dataset("princeton-nlp/SWE-bench_Lite")
    # TODO: seems like in my local env I'm struggling with two packages causing run fails
    # 0-2 types-pkg_resources
    # 10 Failed to build h5py

    #export PYTHONPATH=/<path to SWE-agent directory>/SWE-agent

    mode = ["mini","sonnet","L3.1-70b-Together","L3.1-405b-BaseTen", "L3.1-70b-BaseTen", 'L3.1-70b-Groq'][3]
    if mode == "mini":
        model_name = "gpt-4o-mini"
        cost_limit = 0.05
    elif mode == "sonnet":
        model_name = "claude-3-5-sonnet-20240620"
        cost_limit = 1
    elif mode == "L3.1-70b-Together":
        model_name = "L3.1-70b-Together"
        cost_limit = 0.50
    elif mode == "L3.1-405b-BaseTen":
        model_name = "L3.1-405b-BaseTen"
        cost_limit = 1.0
    elif mode == "L3.1-70b-BaseTen":
        model_name = "L3.1-70b-BaseTen"
        cost_limit = 1.0
    elif mode == "L3.1-70b-Groq":
        model_name = "L3.1-70b-Groq"
        cost_limit = 1.0
    run_agent = False
    evaluate_agent = True
    split = "dev"
    first_question_index = 0
    last_question_index = 23
    ids = ['pvlib__pvlib-python-1072']

    runnable_problems_by_split = get_runnable_problems(
        f"trajectories/{getuser()}/{model_name}__SWE-bench_Lite__default__t-0.00__p-0.95__c-0.05__install-1"
    )
    print("Model name: ", model_name)
    print({k: len(v) for k, v in runnable_problems_by_split.items()})

    if run_agent:
        for question_index in range(first_question_index, last_question_index):
            if len(ids) > 0 and d[split][question_index]["instance_id"] not in ids:
                continue
            print("Running agent for question index: ", question_index)
            print(d[split][question_index]["instance_id"])
            run_and_catch_logs(model_name=model_name, instance=d[split][question_index]["instance_id"], cost_limit=cost_limit, split=split)
    if evaluate_agent:
        import time

        t0 = time.time()
        splits = ["dev", "test"]
        for split in splits:
            print("Running evaluation for split: ", split)
            run_swebench_evaluation(
                predictions_path_override=None,
                model_name=model_name,
                full_dataset_name="princeton-nlp/SWE-bench_Lite",
                cost_limit=cost_limit,
                temperature=0.00,
                top_p=0.95,
                run_id="test",
                split=split,
                max_workers=2,
                full_dataset=d
            )
        print("Time taken: ", time.time() - t0)
        # 9.560726881027222 - cached 14/0
        #
    # Successes so far
    # gpt-4o-mini
    # dev
    # • pvlib__pvlib-python-1072
    # • pydicom__pydicom-1694
    # test 
    # • astropy__astropy-14995

    # claude-3-5-sonnet-20240620

    # L3.1-70b-Together

    # L3.1-405b-BaseTen

    # ERROR: No matching distribution found for vtk

    # TODO
    # get successes with sonnet and mini
    # try out L3.1-70b with 128k context to see where it stacks up
