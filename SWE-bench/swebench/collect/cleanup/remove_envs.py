#!/usr/bin/env python

import argparse
import os
import subprocess

from multiprocessing import Pool


def get_conda_env_names(output: str) -> list:
    """
    Parse conda environments (`conda env list`) created for a particular conda installation

    Args:
        output (str): Output of `conda env list` command
    """
    lines = output.split("\n")
    env_names = []
    for line in lines:
        if line.startswith("#"):
            continue
        if line.strip() == "":
            continue
        if " " in line:
            env_name = line.split(" ")[0]
            env_names.append(env_name)
    return [x for x in env_names if len(x) > 0]


def delete_folders_with_prefix(prefix, conda_path):
    """
    Find and rm folders with a particular prefix in the conda installation's env folder

    Args:
        prefix (str): Prefix of folders to remove
        conda_path (str): Path to conda installation
    """
    envs_folder = os.path.join(conda_path, "envs")
    command = f'find {envs_folder} -type d -name "{prefix}*" -exec rm -rf {{}} +'
    subprocess.run(command.split(" "))


def remove_environment(env_name, prefix):
    """
    Remove all conda environments with a particular prefix from a conda installation
    """
    if env_name.startswith(prefix):
        print(f"Removing {env_name}")
        conda_cmd = "conda remove -n " + env_name + " --all -y"
        cmd = conda_source + " && " + conda_cmd
        try:
            conda_create_output = subprocess.run(cmd.split(), check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            print(f"Error output: {e.stderr}")
            raise e
        print(f"Output: {conda_create_output.stdout}")


if __name__ == "__main__":
    """
    Logic for removing conda environments and their folders from a conda installation
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", type=str, help="Prefix for environments to delete")
    parser.add_argument(
        "--conda_path",
        type=str,
        help="Path to miniconda installation",
    )
    args = parser.parse_args()

    # Remove conda environments with a specific prefix
    conda_source = "source " + os.path.join(args.conda_path, "etc/profile.d/conda.sh")
    check_env = conda_source + " && " + "conda env list"
    try:
        conda_envs = subprocess.run(check_env.split(" "), check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Error output: {e.stderr.decode('utf-8')}")
        raise e
    conda_envs_names = get_conda_env_names(conda_envs.stdout.decode("utf-8"))

    # Remove conda environments in parallel
    num_processes = 25
    pool = Pool(num_processes)
    pool.starmap(
        remove_environment, zip(conda_envs_names, [args.prefix] * len(conda_envs_names))
    )

    # Remove env folder with the same prefix
    print(
        f"Removing miniconda folder for environments with {args.prefix} from {args.conda_path}"
    )
    delete_folders_with_prefix(args.prefix, args.conda_path)
    print(f"Done!")
