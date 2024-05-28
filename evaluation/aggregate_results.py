from __future__ import annotations

import argparse
import glob
import json
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from pathlib import Path

from rich import print

COLUMNS = [
    "Model",
    "Dataset",
    "Setup",
    "Temp.",
    "Top P",
    "Cost",
    "Install",
    "Run",
    "Not Generated",
    "Generated",
    "Applied",
    "Resolved",
    "Resolved IDs",
    "Costs Success",
    "Costs Failure",
    "Costs Overall",
]


def get_folders(path):
    return [entry for entry in Path(path).iterdir() if entry.is_dir()]


def parse_folder_name(folder_name):
    """
    Parse the folder name to get the different parts
    """
    parsed_folder = folder_name.split("__")
    if len(parsed_folder) == 7:
        parsed_folder.append("")
    return parsed_folder


def convert_experiments_to_rows(folder_name, runs_max):
    """
    Convert each experiment to a row in the csv
    """
    rows = []
    directories = get_folders(folder_name)
    for directory in directories:
        folders = get_folders(directory)
        for folder in folders:
            # Skip debug folders
            if "debug" in folder.name:
                continue

            # Skip fine tuned models
            if "ft_gpt-3.5" in folder.name:
                continue

            # Skip folders without a results.json file
            json_file = folder / "results.json"
            if not json_file.exists():
                # print(f"No json file in {folder}")
                continue

            # Extract run attributes
            folder_data = parse_folder_name(folder.name)
            model = folder_data[0]
            dataset = folder_data[1]
            if dataset.startswith("swe-bench-dev-easy-"):
                dataset = dataset[len("swe-bench-dev-easy-") :]
            elif dataset.startswith("swe-bench-dev-"):
                dataset = dataset[len("swe-bench-dev-") :]
            setup = folder_data[2]
            if len(folder_data) != 8:
                # TODO: This might be too strict?
                continue
            temperature = float(folder_data[3][len("t-") :].strip())
            top_p = float(folder_data[4][len("p-") :].strip())
            cost = float(folder_data[5][len("c-") :].strip())
            install = "Y" if folder_data[6].strip() == "install-1" else "N"

            # Parse out run number
            run = folder_data[-1]
            if "run" not in run:
                continue

            try:
                if "run-" in run:
                    run = int(run.split("run-")[-1].split("-")[0].replace("_", "").strip())
                else:
                    run = int(run.split("run")[-1].split("-")[0].replace("_", "").strip())
            except Exception as e:
                print(run)
                raise e

            if runs_max is not None and run > runs_max:
                continue

            # Load results.json file
            with json_file.open() as file:
                results_data = json.load(file)
            report = results_data.get("report", {})

            # Extract resolved ids (to calculate pass@k)
            resolved_ids = []
            if "resolved" in results_data and isinstance(results_data["resolved"], list):
                resolved_ids = results_data["resolved"]
            elif "counts" in results_data and isinstance(results_data["counts"]["resolved"], list):
                resolved_ids = results_data["counts"]["resolved"]

            # Extract instance costs from trajectories
            costs_overall = []
            costs_success = []
            costs_failure = []
            for x in glob.glob(os.path.join(str(folder), "*.traj")):
                traj_data = json.load(open(x))
                if "model_stats" not in traj_data["info"]:
                    continue
                run_cost = traj_data["info"]["model_stats"]["instance_cost"]
                inst_id = x.split("/")[-1].split(".")[0]
                costs_overall.append(run_cost)
                if inst_id in resolved_ids:
                    costs_success.append(run_cost)
                else:
                    costs_failure.append(run_cost)

            # Create run row, write to csv
            rows.append(
                [
                    model,
                    dataset,
                    setup,
                    temperature,
                    top_p,
                    cost,
                    install,
                    run,
                    report.get("# Not Generated", 0),
                    report.get("# Generated", 0),
                    report.get("# Applied", 0),
                    report.get("# Resolved", 0),
                    resolved_ids,
                    costs_success,
                    costs_failure,
                    costs_overall,
                ],
            )

    return rows


def get_results_df(folder_name, runs_max):
    rows = convert_experiments_to_rows(folder_name, runs_max)
    return pd.DataFrame(rows, columns=COLUMNS).sort_values(by=COLUMNS[:8])


def get_results_csv(folder_name):
    get_results_df(folder_name).to_csv("results.csv")
    print("Experiment results written to results.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate results from experiments")
    parser.add_argument("--folder", type=str, help="Folder containing experiment results", default="../trajectories")
    parser.add_argument("--model", nargs="+", type=str, help="Model(s) to filter results by.")
    parser.add_argument("--dataset", nargs="+", type=str, help="Dataset to filter results by.")
    parser.add_argument("--setup", nargs="+", type=str, help="Setup to filter results by.")
    parser.add_argument("--runs_min", type=int, help="Minimum number of runs that experiment should have been run for.")
    parser.add_argument("--runs_max", type=int, help="Maximum number of runs taken into account")
    args = parser.parse_args()

    df = get_results_df(args.folder, args.runs_max)

    grouped_data = (
        df.groupby(COLUMNS[:7])
        .agg(
            {
                "Run": "count",  # Count the number of runs
                "Not Generated": "mean",
                "Generated": "mean",
                "Applied": "mean",
                "Resolved": "mean",
                "Resolved IDs": lambda x: len({item for sublist in x for item in sublist}),
                "Costs Success": lambda x: np.mean([item for sublist in x for item in sublist]),
                "Costs Failure": lambda x: np.mean([item for sublist in x for item in sublist]),
                "Costs Overall": lambda x: np.mean([item for sublist in x for item in sublist]),
            },
        )
        .round(2)
        .reset_index()
        .rename(columns={"Resolved IDs": "Pass@K", "Run": "Runs"})
    )

    # Filtering
    if args.model:
        grouped_data = grouped_data[grouped_data["Model"].isin(args.model)]
    if args.dataset:
        grouped_data = grouped_data[grouped_data["Dataset"].isin(args.dataset)]
    if args.setup:
        grouped_data = grouped_data[grouped_data["Setup"].isin(args.setup)]
    if args.runs_min:
        grouped_data = grouped_data[grouped_data["Run"] >= args.runs_min]

    print(f"Total experiments run: {grouped_data.shape[0]}")
    grouped_data_sorted = grouped_data.sort_values(by=["Dataset", "Resolved"], ascending=[True, False])
    pd.set_option("display.max_rows", None)
    grouped = grouped_data_sorted.groupby("Dataset")

    for name, group in grouped:
        print(f"\n-----------------\nDataset: {name}\n-----------------")
        print(group.to_string(index=False))
