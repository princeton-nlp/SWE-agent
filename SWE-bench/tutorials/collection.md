# Collecting Evaluation Tasks for SWE-Bench
John Yang &bull; November 1, 2023

In this tutorial, we explain how to use the SWE-Bench repository to collect evaluation task instances from GitHub repositories.

> SWE-bench's collection pipeline is currently designed to target PyPI packages. We hope to expand SWE-bench to more repositories and languages in the future.

<div align="center">
    <img style="width:70%" src="../assets/collection.png">
</div>

## 🔍 Selecting a Repository

SWE-bench constructs task instances from issues and pull requests.
A good repository to source evaluation instances from should have many issues and pull requests.
A point of reference for repositories that fit this bill would be the [Top PyPI packages](https://hugovk.github.io/top-pypi-packages/) website.

Once you've selected a repository, use the `/collect/make_repo/make_repo.sh` script to create a mirror of the repository, like so:
```bash
./collect/make_repo/make_repo.sh scikit-learn/scikit-learn
```

## ⛏️ Collecting Candidate Tasks

Once you have cloned the repository, you can then use the `collect/get_tasks_pipeline.py` script to collect pull requests and convert them to candidate task instances.
Supply the *repository name(s)* and *logging folders* as arguments to the `run_get_tasks_pipeline.sh` script, then run it like so:
```bash
./collect/run_get_tasks_pipeline.sh 
```

At this point, for a repository, you should have...
* A mirror clone of the repository under the [SWE-bench organization](https://github.com/orgs/swe-bench/repositories).
* A `<repo name>-prs.jsonl` file containing all the repository's PRs.
* A `<repo name>-task-instances.jsonl` file containing all the candidate task instances.

## 📙 Specify Execution Parameters

This step is the most manual of all parts.
To create an appropriate execution environment for task instances from a new repository, you must do the following steps:
* Assign a repository-specific *version* (i.e. `1.2`) to every task instance.
* Specify repository+version-specific installation commands in `harness/constants.py`.

### Part A: Versioning
Determining a version for each task instance can be accomplished in a number of ways, depending on the availability + feasability with respect to each repository.
* Scrape from code: A version is explicitly specified in the codebase (in `__init__.py` or `_version.py` for PyPI packages).
* Scrape from web: Repositories with websites (i.e. [xarray.dev](https://xarray.dev/)) have a "Releases" or "What's New" page (i.e. [release page](https://docs.xarray.dev/en/stable/whats-new.html) for xarray). This can be scraped for information.
* Build from code: Sometimes, version-related files (i.e. `_version.py`) are purposely omitted by a developer (check `.gitignore` to verify). In this case, per task instance you can build the repository source code locally and extract the version number from the built codebase.

Examples and technical details for each are included in `/versioning/`. Please refer to them as needed.

### Part B: Installation Configurations
Per repository, you must provide installation instructions per version. In `constants.py`...
1. In `MAP_VERSION_TO_INSTALL`, declare a `<repo owner/name>: MAP_VERSION_TO_INSTALL_<repo name>` key/value pair.
2. Define a `MAP_VERSION_TO_INSTALL_<repo name>`, where the key is a version as a string, and the value is a dictionary of installation fields that include the following information:
```python
{
    "python": "3.x", # Required
    "packages": "numpy pandas tensorflow",
    "install": "pip install -e .", # Required
    "pip_packages": ["pytest"],
}
```
These instructions can typically be inferred from the companion website or `CONTRIBUTING.md` doc that many open source repositories have.

## ⚙️ Execution-based Validation
Congrats, you got through the trickiest part! It's smooth sailing from here on out.

We now need to check that the task instances install properly + the problem solved by the task instance is non-trivial.
This is taken care of by the `engine_validation.py` code.
Run `./harness/run_validation.sh` and supply the following arguments:
* `instances_path`: Path to versioned candidate task instances
* `log_dir`: Path to folder to store task instance-specific execution logs
* `temp_dir`: Path to directory to perform execution
* `verbose`: Whether to print logging traces to standard output.

> In practice, you may have to iterate between this step and **Installation Configurations** a couple times. If your instructions are incorrect/under-specified, it may result in candidate task instances not being installed properly.

## 🔄 Convert to Task Instances
At this point, we now have all the information necessary to determine if task instances can be used for evaluation with SWE-bench, and save them if they do.

We provide the `validation.ipynb` Jupyter notebook provided in this folder to make the remaining steps easier.
At a high level, it enables the following:
* In **Monitor Validation**, check the results of the `./run_validation.sh` step.
* In **Get [FP]2[FP] Tests**, determine which task instances are non-trivial (solves at least one test)
* In **Create Task Instances `.json` file**, perform some final preprocessing and save your task instances to a `.json` file.

Thanks for reading! If you have any questions or comments about the details in the article, please feel free to follow up with an issue.
