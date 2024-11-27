from __future__ import annotations

import os
import shutil

from datasets import load_dataset


def copy_to_subdirs(source_file: str, target_dir: str) -> None:
    """
    Copy a file to all subdirectories in a given directory.

    Args:
        source_file: Path to the file to copy
        target_dir: Directory containing subdirectories to copy to
    """
    # Verify source file exists
    if not os.path.isfile(source_file):
        raise FileNotFoundError(f"Source file {source_file} does not exist")

    os.makedirs(target_dir, exist_ok=True)
    # Verify target directory exists
    if not os.path.isdir(target_dir):
        raise NotADirectoryError(f"Target directory {target_dir} does not exist")

    # Get source filename
    filename = os.path.basename(source_file)

    # Get all immediate subdirectories
    subdirs = [
        "simply",
        "wcwidth",
        "parsel",
        "chardet",
        "minitorch",
        "tinydb",
        "deprecated",
        "voluptuous",
        "cachetools",
        "imapclient",
        "marshmallow",
        "jinja",
        "cookiecutter",
        "portalocker",
        "pyjwt",
        "babel",
        "statsmodels",
        "python-progressbar",
        "xarray",
        "imbalanced-learn",
        "web3.py",
        "scrapy",
        "seaborn",
        "pypdf",
        "pexpect",
        "pytest",
        "pylint",
        "joblib",
        "dulwich",
        "virtualenv",
        "networkx",
        "requests",
        "sphinx",
        "jedi",
        "moviepy",
        "loguru",
        "paramiko",
        "geopandas",
        "bitstring",
        "fastapi",
        "tornado",
        "python-prompt-toolkit",
        "attrs",
        "PyBoy",
        "pydantic",
        "filesystem_spec",
        "tlslite-ng",
        "graphene",
        "mimesis",
        "dnspython",
        "python-rsa",
        "more-itertools",
        "click",
        "fabric",
        "flask",
        "sqlparse",
    ]

    # Copy file to each subdirectory
    for idx, subdir in enumerate(subdirs):
        target_path = os.path.join(target_dir, subdir, filename.replace(".md", f"_{subdir}.md"))
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        try:
            shutil.copy2(source_file, target_path)
            print(f"Copied {filename} to {subdir}")
        except Exception as e:
            print(f"Failed to copy to {subdir}: {str(e)}")


commit0_dataset = load_dataset("wentingzhao/commit0_combined", split="test")

file = "commit0_prepare/my_issue.md"
target_dir = "commit0_prepare/repos/"

copy_to_subdirs(file, target_dir)

# Create directory if it doesn't exist
os.makedirs("config/commands/commit0/", exist_ok=True)

for i in commit0_dataset:
    repo_name = i["repo"].split("/")[1]
    test_cmd = i["test"]["test_cmd"]
    test_dir = i["test"]["test_dir"]
    src_dir = i["src_dir"]
    base_commit = i["base_commit"]
    reset_cmd = f"git reset --hard {base_commit}"
    # submit_cmd = f"`git diff {base_commit} -- . ':(exclude)spec.pdf.bz2' > /patch.diff`"

    submit_sh = f"{repo_name}_submit.sh"
    # Read the default yaml file
    with open("commit0_prepare/default_from_url_commit0.yaml") as f:
        yaml_content = f.read()

    yaml_content = yaml_content.replace("{src_dir}", f"{src_dir}")
    # Replace {test_cmd} with actual test command and directory
    yaml_content = yaml_content.replace("{test_cmd}", f"{test_cmd}")
    yaml_content = yaml_content.replace("{test_dir}", f"{test_dir}")
    yaml_content = yaml_content.replace("{git_reset}", f"{reset_cmd}")
    # yaml_content = yaml_content.replace('{submit_cmd}', f'{submit_cmd}')
    yaml_content = yaml_content.replace("{submit.sh}", f"{submit_sh}")

    submit_path = f"config/commands/commit0/{repo_name}_submit.sh"

    # Create submit.sh content for this repo
    submit_content = f"""# @yaml
# signature: submit
# docstring: submits your current code and terminates the session
submit() {{
    cd /testbed

    git add -A
    git diff {base_commit} -- . ':(exclude)spec.pdf.bz2' > model.patch
    echo "<<SUBMISSION||"
    cat model.patch
    echo "||SUBMISSION>>"
}}
"""
    # Write submit.sh file
    with open(submit_path, "w") as f:
        f.write(submit_content)
    # Create new yaml file for this repo
    output_path = f"config/commit0/prompt/{repo_name}.yaml"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(yaml_content)
