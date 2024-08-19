"""Replay a trajectory"""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

import yaml

import run as runscript


def process_single_traj(traj_path: str, config_file: str, data_path: str, suffix: str, *, forward_args: list[str]):
    """

    Args:
        traj_path (str): _description_
        config_file (str): _description_
        data_path (str): _description_
        suffix (str): _description_
        forward_args (List[str]): Passed to run.py

    Raises:
        ValueError: Incorrect paths or other config issue

    Returns:
        None
    """
    replay_action_trajs_path = "temp_replay.jsonl"

    # Open trajectory file, extract responses as actions
    if traj_path.endswith(".yaml"):
        traj_data = dict()
        with open(traj_path) as f:
            traj_data["history"] = yaml.safe_load(f)
    else:
        with open(traj_path) as file:
            traj_data = json.load(file)
    actions = [x["content"] for x in traj_data["history"] if x["role"] == "assistant"]
    instance_id = traj_path.split("/")[-1].split(".")[0]
    with open(replay_action_trajs_path, "w") as f:
        print(json.dumps({instance_id: actions}), file=f, end="\n", flush=True)

    # Get data_path from args.yaml
    if data_path is None:
        args_path = os.path.join(os.path.dirname(traj_path), "args.yaml")
        with open(args_path) as f:
            args = yaml.safe_load(f)
        data_path = args["environment"]["data_path"]

    # Identify the relevant task instance and create it
    def create_task_instances_tmp_file(data: list[dict[str, Any]]) -> str:
        """Helper function to create a temporary file to write task instances to.
        Returns path to the temporary file.
        """
        data = [d for d in data if d["instance_id"] == instance_id]
        tmp_path = instance_id + ".jsonl"
        with open(tmp_path, "w") as f:
            for d in data:
                print(json.dumps(d), file=f, end="\n", flush=True)
        return tmp_path

    is_other = False
    if data_path.endswith(".jsonl"):
        replay_task_instances_path = create_task_instances_tmp_file(
            [json.loads(x) for x in Path(data_path).read_text().splitlines(keepends=True)],
        )
    elif data_path.endswith(".json"):
        with open(data_path) as file:
            data = json.load(file)
        replay_task_instances_path = create_task_instances_tmp_file(data)
    else:
        # Assume data_path is a github url or local url
        is_other = True
        replay_task_instances_path = data_path

    # Call run.py via subprocess
    run_args = [
        "--config_file",
        config_file,
        "--data_path",
        replay_task_instances_path,
        "--install_environment",
        "True",
        "--model_name",
        "replay",
        "--replay_path",
        replay_action_trajs_path,
        *forward_args,
    ]
    if is_other:
        # Not sure if this only applies to github urls for data_path
        run_args.extend(["--skip_existing", "False"])
    if suffix is not None:
        run_args.extend(["--suffix", suffix])
    script_args = runscript.get_args(run_args)
    runscript.main(script_args)

    os.remove(replay_action_trajs_path)
    if not is_other:
        os.remove(replay_task_instances_path)


def main(
    traj_path: str,
    config_file: str,
    data_path: str,
    suffix: str,
    *,
    forward_args: list[str],
):
    process_single_traj(traj_path, config_file, data_path, suffix, forward_args=forward_args)


def get_args(args=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--traj_path", help="Path to trajectory to replay", required=True)
    parser.add_argument("--config_file", help="Path to template", required=True)
    parser.add_argument(
        "--data_path",
        help="(Optional) Path to data file containing task instances ref'ed by replay trajectories",
        default=None,
    )
    parser.add_argument("--suffix", help="(Optional) Suffix argument appended to end of traj path", default=None)
    args, remaining_args = parser.parse_known_args(args=args)
    return args, remaining_args


if __name__ == "__main__":
    args, remaining_args = get_args()
    main(**vars(args), forward_args=remaining_args)
