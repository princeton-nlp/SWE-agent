#!/usr/bin/env python3

import subprocess

repos = ["Repos here"]

for repo in repos:
    print(f"Making mirror repo for {repo}")
    out_make = subprocess.run(
        f"./make_repo.sh {repo}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if out_make.returncode != 0:
        print(f"Error making mirror repo for {repo}")
    else:
        print(f"Success making mirror repo for {repo}")
