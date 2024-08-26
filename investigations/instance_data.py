from __future__ import annotations

import hashlib
import sys

import pandas as pd


def get_swe_bench_data():
    return pd.read_parquet("hf://datasets/princeton-nlp/SWE-bench_Verified/data/test-00000-of-00001.parquet")


def generate_cached_image_id(instance_id: str, environment_setup: str = "no_setup") -> str:
    cached_image_prefix = "swe-agent-task-env-"

    # Get the DataFrame
    df = get_swe_bench_data()

    # Find the row with the matching instance_id
    row = df[df["instance_id"] == instance_id]

    if row.empty:
        msg = f"No data found for instance_id: {instance_id}"
        raise ValueError(msg)

    # Pull repo and base_commit from the DataFrame
    repo = row["repo"].iloc[0]
    base_commit = row["base_commit"].iloc[0]

    # Create inputs list and generate final label
    inputs: list[str] = [
        repo,
        base_commit,
        environment_setup,
    ]
    tag = hashlib.sha256("".join(inputs).encode()).hexdigest()[:50]
    image_id = f"{cached_image_prefix}{tag}"

    return image_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python instance_data.py <instance_id> [environment_setup]")
        sys.exit(1)

    instance_id = sys.argv[1]
    environment_setup = sys.argv[2] if len(sys.argv) > 2 else "no_setup"

    result = generate_cached_image_id(instance_id, environment_setup)
    print(result)

