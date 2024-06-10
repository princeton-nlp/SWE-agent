#!/usr/bin/env python3

"""Given the `<owner/name>` of a GitHub repo, this script writes the raw information for all the repo's PRs to a single `.jsonl` file."""

import argparse
import json
import logging
import os
from typing import Optional

from fastcore.xtras import obj2dict
from swebench.collect.utils import Repo

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def log_all_pulls(repo: Repo, output: str):
    """
    Iterate over all pull requests in a repository and log them to a file

    Args:
        repo (Repo): repository object
        output (str): output file name
    """
    with open(output, "w") as output:
        for pull in repo.get_all_pulls():
            setattr(pull, "resolved_issues", repo.extract_resolved_issues(pull))
            print(json.dumps(obj2dict(pull)), end="\n", flush=True, file=output)


def main(repo_name: str, output: str, token: Optional[str] = None):
    """
    Logic for logging all pull requests in a repository

    Args:
        repo_name (str): name of the repository
        output (str): output file name
        token (str, optional): GitHub token
    """
    if token is None:
        token = os.environ["GITHUB_TOKEN"]
    owner, repo = repo_name.split("/")
    repo = Repo(owner, repo, token=token)
    log_all_pulls(repo, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_name", type=str, help="Name of the repository")
    parser.add_argument("output", type=str, help="Output file name")
    parser.add_argument("--token", type=str, help="GitHub token")
    args = parser.parse_args()
    main(**vars(args))
