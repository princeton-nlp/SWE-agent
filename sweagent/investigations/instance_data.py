from __future__ import annotations

import hashlib
import sys

import pandas as pd


def get_swe_bench_data():
    return pd.read_parquet("hf://datasets/princeton-nlp/SWE-bench_Verified/data/test-00000-of-00001.parquet")

def truncate_string(text, max_length=100):
    return (text[:max_length] + '...') if len(text) > max_length else text

def get_swe_bench_instance_markdown(instance_id: str):
    # Get the DataFrame
    df = get_swe_bench_data()
    
    # Select the specific row
    specific_row = df[df['instance_id'] == instance_id]
    
    if specific_row.empty:
        return "No data found for the given instance_id."
    
    # Truncation
    if 'PASS_TO_PASS' in specific_row.columns:
       specific_row.loc[:, 'PASS_TO_PASS'] = specific_row['PASS_TO_PASS'].apply(truncate_string)
    
    # Transpose the row
    transposed = specific_row.transpose()
    
    # Reset the index to turn the column names into a regular column
    transposed = transposed.reset_index()
    
    # Rename the columns
    transposed.columns = ['Field', 'Value']
    
    # Convert to Markdown
    return transposed.to_markdown(index=False)

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
    return image_id  # noqa: RET504


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python instance_data.py <instance_id> [environment_setup]")
        sys.exit(1)

    instance_id = sys.argv[1]
    environment_setup = sys.argv[2] if len(sys.argv) > 2 else "no_setup"

    result = generate_cached_image_id(instance_id, environment_setup)
    print(result)

