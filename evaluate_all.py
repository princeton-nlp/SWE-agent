import argparse
import json
import subprocess
from datasets import load_dataset  # type: ignore
import pandas as pd


def run_argo(data_path: str, instance_ids: list[str], split: str):
    # Step 3: Create the Argo Workflow YAML
    workflow_template = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "generateName": "swe-eval-"
        },
        "spec": {
            "entrypoint":
            "evaluate-workflow",
            "templates": [{
                "name": "evaluate-instances",
                "inputs": {
                    "parameters": [{
                        "name": "instance_id"
                    }]
                },
                "metadata": {
                    "labels": {
                        "app": "swe-eval"
                    }
                },
                "container": {
                    "image":
                    "gcr.io/reflectionai/swe-eval:latest",
                    "command": ["python"],
                    "args": [
                        "/evaluate_one.py",
                        "--data_path",
                        data_path,
                        "--instance_id",
                        "{{inputs.parameters.instance_id}}",
                        "--split",
                        split,
                    ]
                },
                "affinity": {
                    "podAntiAffinity": {
                        "requiredDuringSchedulingIgnoredDuringExecution": [{
                            "labelSelector": {
                                "matchExpressions": [{
                                    "key": "app",
                                    "operator": "In",
                                    "values": ["swe-eval"]
                                }]
                            },
                            "topologyKey":
                            "kubernetes.io/hostname"
                        }]
                    }
                }
            }, {
                "name":
                "evaluate-workflow",
                "steps": [[{
                    "name": "evaluate-step",
                    "template": "evaluate-instances",
                    "arguments": {
                        "parameters": [{
                            "name": "instance_id",
                            "value": "{{item}}"
                        }]
                    },
                    "withItems": instance_ids
                }]]
            }]
        }
    }

    # Write the workflow to a file
    with open('/tmp/workflow.yaml', 'w') as f:
        json.dump(workflow_template, f, indent=2)

    # Step 4: Submit the workflow using argo submit
    subprocess.run(["argo", "submit", "/tmp/workflow.yaml", "--watch"])


def run_loop(data_path: str, instance_ids: list[str], split: str):
    for instance_id in instance_ids:
        subprocess.run(
            f"docker run --rm -it gcr.io/reflectionai/swe-eval:latest python /evaluate_one.py --data_path {data_path} --instance_id {instance_id} --split {split}"
            .split())


def main(argo: bool, data_path: str, split: str):
    # Step 1: Load the dataset
    dataset: pd.DataFrame = load_dataset(
        data_path)[split].to_pandas()  # type: ignore

    # Step 2: Extract the list of instance_ids
    instance_ids: list[str] = dataset['instance_id'].to_list()

    if argo:
        run_argo(data_path=data_path, instance_ids=instance_ids, split=split)
    else:
        run_loop(data_path=data_path, instance_ids=instance_ids, split=split)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path",
                        type=str,
                        default="princeton-nlp/SWE-bench_Lite")
    parser.add_argument("--split", type=str, required=True)
    parser.add_argument("--argo", action="store_true")
    args = parser.parse_args()
    main(argo=args.argo, data_path=args.data_path, split=args.split)
