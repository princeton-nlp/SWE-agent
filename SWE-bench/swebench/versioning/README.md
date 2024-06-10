# Versioning
To enable execution based evaluation, SWE-bench assigns each task instances a `version` (with respect to its repository), where the `version` is then a key for the installation instructions.

This folder contains code for assigning the version of a task instance based on its repository.

## 🔧 General Purpose
`get_versions.py` script is a general purpose tool for getting version from either A. reading the GitHub repository or B. from building the repository locally and locating the appropriate version files.
Given a list of candidate task instances, the script assigns each task instance a new `version: <value>` key/value pair.

This script can be invoked via the `./run_get_version.sh` script, where the arguments are:
```
python get_versions.py \
    --instances_path   [Required] [folder] Patch to candidate task instances \
    --retrieval_method [Required] [choice] Method to retrieve versions ("build", "mix", or "github") \
    --cleanup          [Required] [bool]   Remove testbed and conda environments upon task completion \
    --conda_env        [Required] [str]    Name of conda environment to run task installation within \
    --num_workers      [Required] [int]    Number of processes to parallelize on \
    --path_conda       [Required] [folder] Path to miniconda or anaconda installation \
    --output_dir       [Required] [folder] Path to directory to write versioned task instances to (overwrite by default) \
    --testbed          [Required] [folder] Path to testbed directory, for cloning GitHub repos to
```

## 🌐 Repository Website-Based
The `extract_web/get_versions_*.py` files are repository specific scripts that crawl the website of the PyPI package to find versions and their cut off dates.
This script can be easily adapted to other repositories to check task instances' `creation_date` against the version dates.