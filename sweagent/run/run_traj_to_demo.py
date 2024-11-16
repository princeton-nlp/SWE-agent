from __future__ import annotations

import io
import json
from argparse import ArgumentParser
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString as LSS

DEMO_COMMENT = """# This is a demo file generated from trajectory file:
# {traj_path}
# You can use this demo file to replay the actions in the trajectory with run_replay.py.
# You can edit the content of the actions in this file to modify the replay behavior.
# NOTICE:
#         Only the actions of the assistant will be replayed.
#         You do not need to modify the observation's contents or any other fields.
#         You can add or remove actions to modify the replay behavior."""


def convert_to_literal_string(d):
    """
    Convert any multi-line strings to LiteralScalarString
    """
    if isinstance(d, dict):
        for key, value in d.items():
            if isinstance(value, str) and "\n" in value:
                d[key] = LSS(value.replace("\r\n", "\n").replace("\r", "\n"))
            elif isinstance(value, dict):
                convert_to_literal_string(value)
    elif isinstance(d, list):
        for i, item in enumerate(d):
            if isinstance(item, str) and "\n" in item:
                d[i] = LSS(item.replace("\r\n", "\n").replace("\r", "\n"))
            elif isinstance(item, dict):
                convert_to_literal_string(item)
    elif isinstance(d, str) and "\n" in d:
        d = LSS(d.replace("\r\n", "\n").replace("\r", "\n"))
    else:
        msg = f"Unsupported type: {type(d)}"
        raise ValueError(msg)
    return d


def save_demo(data, file, traj_path):
    """
    Save a single task instance as a yaml file
    """
    data = convert_to_literal_string(data)
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    content = buffer.getvalue()
    header = DEMO_COMMENT.format(traj_path=traj_path)
    with open(file, "w") as f:
        f.write(f"{header}\n{content}")


def convert_traj_to_action_demo(traj_path: str, output_file: str | Path, include_user: bool = False):
    with open(traj_path) as file:
        traj = json.load(file)

    history = traj["history"]
    action_traj = list()
    admissible_roles = {"assistant", "user"} if include_user else {"assistant"}
    for step in history:
        if step["role"] in admissible_roles and step.get("agent", "primary") == "primary":
            action_traj.append({k: v for k, v in step.items() if k in {"content", "role"}})
    save_demo(action_traj, output_file, traj_path)
    print(f"Saved demo to {output_file}")


def main(traj_path: str, output_dir: str, suffix: str = "", overwrite: bool = False, include_user: bool = False):
    filename = (
        "/".join([Path(traj_path).parent.name + suffix, Path(traj_path).name.rsplit(".traj", 1)[0]]) + ".demo.yaml"
    )
    output_file = Path(output_dir) / filename
    if output_file.exists() and not overwrite:
        msg = f"Output file already exists: {output_file}"
        raise FileExistsError(msg)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    convert_traj_to_action_demo(traj_path, output_file, include_user)


def string2bool(s):
    if s.lower() in {"true", "1"}:
        return True
    elif s.lower() in {"false", "0"}:
        return False
    else:
        msg = f"Invalid boolean string: {s}"
        raise ValueError(msg)


def run_from_cli(args: list[str] | None = None):
    parser = ArgumentParser()
    parser.add_argument("traj_path", type=str, help="Path to trajectory file")
    parser.add_argument("--output_dir", type=str, help="Output directory for action demos", default="./demos")
    parser.add_argument("--suffix", type=str, help="Suffix for the output file", default="")
    parser.add_argument("--overwrite", type=string2bool, help="Overwrite existing files", default=False, nargs="?")
    parser.add_argument(
        "--include_user",
        type=string2bool,
        help="Include user responses (computer)",
        default=False,
        nargs="?",
    )
    parsed_args = parser.parse_args(args)
    main(**vars(parsed_args))


if __name__ == "__main__":
    run_from_cli()
