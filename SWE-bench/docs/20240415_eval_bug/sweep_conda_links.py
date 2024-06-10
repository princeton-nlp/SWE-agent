import os
import subprocess

"""
This script is used to sweep through a list of conda links and run the evaluation script on each one.

It was originally invoked from the swebench/harness/ folder.
"""

conda_links = [
  "https://repo.anaconda.com/miniconda/Miniconda3-py39_23.9.0-0-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py311_23.9.0-0-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py310_23.9.0-0-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py39_23.10.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py311_23.10.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py310_23.10.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py38_23.10.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py311_23.11.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py38_23.11.0-1-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-2-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py311_23.11.0-2-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh",
  "https://repo.anaconda.com/miniconda/Miniconda3-py38_23.11.0-2-Linux-x86_64.sh",
]

for conda_link in conda_links:
    version = conda_link.split("/")[-1]\
      .split("-", 1)[1]\
      .rsplit("-", 2)[0]\
      .replace(".", "_")\
      .replace("-", "_")
    os.makedirs(f"/n/fs/p-swe-bench/results/{version}/", exist_ok=True)

    cmd = (
      "python evaluation.py "
      "--predictions_path /n/fs/p-swe-bench/data/original/gold_preds.jsonl "
      "--swe_bench_tasks /n/fs/p-swe-bench/data/original/swe-bench.json "
      f"--log_dir /n/fs/p-swe-bench/results/{version}/ "
      f"--conda_link {conda_link} "
      "--testbed /n/fs/p-swe-bench/testbed/ "
      "--timeout 1200 "
      "--verbose "
    )

    # Run subprocess
    subprocess.run(cmd, shell=True)

    # Move results, scorecard to results/{version} log_dir
    subprocess.run(
      f"mv /n/fs/p-swe-bench/data/original/results.json /n/fs/p-swe-bench/results/{version}/results.json",
      shell=True
    )
    subprocess.run(
      f"mv /n/fs/p-swe-bench/data/original/scorecard.json /n/fs/p-swe-bench/results/{version}/scorecard.json",
      shell=True
    )
    
    # Clear testbed
    subprocess.run(f"rm -rf /n/fs/p-swe-bench/testbed/*", shell=True)
