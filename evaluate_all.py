import argparse
import json
import subprocess
from datasets import load_dataset  # type: ignore
import pandas as pd


def run_loop(data_path: str, instance_ids: list[str], split: str):
    for instance_id in instance_ids:
        subprocess.run(
            f"docker run --rm -it gcr.io/reflectionai/swe-eval:latest python /evaluate_one.py --data_path {data_path} --instance_id {instance_id} --split {split}"
            .split())


def main(data_path: str, split: str):
    # Step 1: Load the dataset
    dataset: pd.DataFrame = load_dataset(
        data_path)[split].to_pandas()  # type: ignore

    # Step 2: Extract the list of instance_ids
    instance_ids: list[str] = dataset['instance_id'].to_list()

    run_loop(data_path=data_path, instance_ids=instance_ids, split=split)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path",
                        type=str,
                        default="princeton-nlp/SWE-bench_Lite")
    parser.add_argument("--split", type=str, required=True)
    args = parser.parse_args()
    main(data_path=args.data_path, split=args.split)
