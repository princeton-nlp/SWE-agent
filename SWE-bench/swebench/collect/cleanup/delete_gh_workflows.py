#!/usr/bin/env python3

import argparse
import os
import subprocess


def main(repo_url):
    """
    Remove .github/workflows folder from all branches of a repo

    Args:
        repo_url (str): URL of the target repo
    """
    # Get list of remote branches
    branches_command = subprocess.run(
        ["git", "ls-remote", "--heads", repo_url], capture_output=True, text=True
    )
    branches = branches_command.stdout.strip().split("\n")
    branches = [branch.split()[1] for branch in branches]
    subprocess.run(
        ["git", "clone", repo_url, "temp_repo"],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    # Iterate through all branches
    os.chdir("temp_repo")
    for branch in branches:
        # Switch to branch
        print(f"--------------\nProcessing branch: {branch}")
        branch = branch.split("/")[-1]
        subprocess.run(["git", "checkout", branch])

        workflows_path = os.path.join(".github", "workflows")
        if os.path.exists(workflows_path):
            # Remove .github/workflows folder if it exists
            print(f"Deleting .github/workflows folder from branch: {branch}")
            subprocess.run(["rm", "-rf", workflows_path])
            subprocess.run(["git", "add", "-A"])
            subprocess.run(["git", "commit", "-m", "Remove .github/workflows folder"])
            subprocess.run(["git", "push"])
        else:
            print(f".github/workflows folder not found in branch: {branch}")

    os.chdir("..")
    subprocess.run(["rm", "-rf", "temp_repo"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_url", type=str, required=True)
    args = parser.parse_args()
    main(**vars(args))
