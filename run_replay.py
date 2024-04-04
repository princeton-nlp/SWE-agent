import json
import os
import subprocess
import yaml

from argparse import ArgumentParser


def process_synthetic_trajs(action_trajs_path: str, config_file: str, suffix: str):
    # Load action trajectories, task instances
    action_trajs = [json.loads(x) for x in open(action_trajs_path, "r").readlines()]
    task_instances = [x["task_instance"] for x in action_trajs]
    file_name = action_trajs_path.rsplit("/", 1)[-1]

    # Temporary file names
    replay_action_trajs_path = "temp_actions.jsonl"
    replay_task_instances_path = file_name

    # Write task_instances to file for data_path
    with open(replay_task_instances_path, "w") as f:
        for t in task_instances:
            print(json.dumps(t), file=f, end="\n", flush=True)

    # Write action trajectories to a file
    with open(replay_action_trajs_path, "w") as f:
        for t in action_trajs:
            print(
                json.dumps({t["task_instance"]["instance_id"]: t["actions"]}),
                file=f,
                end="\n",
                flush=True,
            )

    # Call run.py via subprocess
    command = [
        "python",
        "run.py",
        "--config_file", config_file,
        "--data_path", replay_task_instances_path,
        "--install_environment", "True",
        "--model_name", "replay",
        "--replay_path", replay_action_trajs_path
    ]
    if suffix is not None:
        command.extend(["--suffix", suffix])

    subprocess.run(command)

    os.remove(replay_action_trajs_path)
    os.remove(replay_task_instances_path)


def process_single_traj(traj_path: str, config_file: str, data_path: str, suffix: str):
    replay_action_trajs_path = "temp_replay.jsonl"

    # Open trajectory file, extract responses as actions
    if traj_path.endswith(".yaml"):
        traj_data = dict()
        with open(traj_path, "r") as f:
            traj_data["history"] = yaml.safe_load(f)
    else:
        traj_data = json.load(open(traj_path, "r"))
    actions = [x["content"] for x in traj_data["history"] if x["role"] == "assistant"]
    instance_id = traj_path.split("/")[-1].split(".")[0]
    with open(replay_action_trajs_path, "w") as f:
        print(
            json.dumps({instance_id: actions}),
            file=f,
            end="\n",
            flush=True
        )
    replay_task_instances_path = instance_id + ".jsonl"

    # Get data_path from args.yaml
    if data_path is None:
        args_path = os.path.join(
            os.path.dirname(traj_path),
            "args.yaml"
        )
        args = yaml.safe_load(open(args_path))
        data_path = args['environment']['data_path']

    # Identify the relevant task instance and create it
    data = None
    if data_path.endswith(".jsonl"):
        data = [json.loads(x) for x in open(data_path, "r").readlines()]
    elif data_path.endswith(".json"):
        data = json.load(open(data_path))
    else:
        raise ValueError("--data_path must be a .json or .jsonl")
    data = [d for d in data if d["instance_id"] == instance_id]

    with open(replay_task_instances_path, "w") as f:
        for d in data:
            print(json.dumps(d), file=f, end="\n", flush=True)

    # Call run.py via subprocess
    command = [
        "python",
        "run.py",
        "--config_file", config_file,
        "--data_path", replay_task_instances_path,
        "--install_environment", "True",
        "--model_name", "replay",
        "--replay_path", replay_action_trajs_path,
    ]
    if suffix is not None:
        command.extend(["--suffix", suffix])
    subprocess.run(command)

    # os.remove(replay_action_trajs_path)
    # os.remove(replay_task_instances_path)


def main(
    action_trajs_path: str,
    traj_path: str,
    config_file: str,
    data_path: str,
    suffix: str,
):
    if action_trajs_path is not None:
        process_synthetic_trajs(action_trajs_path, config_file, suffix)
    elif traj_path is not None:
        process_single_traj(traj_path, config_file, data_path, suffix)
    else:
        print(
            "No replays generated.\n"
            "You must either provide one of the following. Either...\n"
            "\t* --action_trajs_path for replaying synthetic trajectories\n"
            "\t* --traj_path for replaying SWE-agent style trajectories (from ./trajectories folder)\n"
        )

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--action_trajs_path", help="Path to action trajectories to replay", default=None)
    parser.add_argument("--traj_path", help="Path to trajectory to replay", default=None)
    parser.add_argument("--config_file", help="Path to template", required=True)
    parser.add_argument("--data_path", help="(Optional) Path to data file containing task instances ref'ed by replay trajectories", default=None)
    parser.add_argument("--suffix", help="(Optional) Suffix argument appended to end of traj path", default=None)
    args = parser.parse_args()
    main(**vars(args))
