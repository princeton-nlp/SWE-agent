# Evaluation Harness Repair Report
April 15, 2024

In this report, we detail our resolution of evaluation harness failures that we and SWE-bench practitioners observed from January 2024 to April 2024.
The root cause of this issue is due to SWE-bench's reliance on underspecified conda installation specifications.
We include details about the failure modes and resolution found in our investigations.
As of this report's release, SWE-bench evaluation has been restored to work properly (`swebench>=1.1.0`).

While the current state is functional for evaluation purposes, we are working on a more permanent solution to ensure that the evaluation harness is robust and reliable for future use.

## Failure Modes
From versions `0.6.9` to `1.0.x`, we were recovering from multiple failures arising when running SWE-bench task instances.
Specifically, we investigated causes for conda based installation failing for the validation and execution harnesses.
The root causes of the issues are as follows:

**1. `latest` Conda Link**: The `latest` conda link, which the harness originally used, is updated overtime to point at different versions. For example, based on the [Miniconda archive](https://repo.anaconda.com/miniconda/), the URL for the latest download (`https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh`) pointed at different links overtime. Also see https://github.com/conda/conda/issues/13701. Due to this change, the conda environment we define for each repo/version may fail to be created at a later date.
- Severity: 🔴 High (100+ Task Instances Affected)
- Affected Repositories: astropy, matplotlib, sympy, sphinx, scikit-learn, requests, xarray

<details>
<summary>Click for Example</summary>
This is an example of the log to console that showed up when the conda environment for sphinx 4.1 failed to build properly.

```bash
❌ Evaluation failed: Command '. /home/ubuntu/SWE-agent/evaluation/testbed/predictions/sphinx-doc__sphinx/4.1/tmpe4u_b189/miniconda3/bin/activate sphinx-doc__sphinx__4.1 && 
conda install gxx_linux-64 gcc_linux-64 make -y' returned non-zero exit status 2.
multiprocessing.pool.RemoteTraceback: 
"""
Traceback (most recent call last):
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/multiprocessing/pool.py", line 125, in worker
    result = (True, func(*args, **kwds))
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/multiprocessing/pool.py", line 48, in mapstar
    return list(map(*args))
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/site-packages/swebench/harness/engine_evaluation.py", line 167, in main
    setup_testbed(data_groups[0])
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/site-packages/swebench/harness/engine_validation.py", line 90, in setup_testbed
    with TestbedContextManager(
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/site-packages/swebench/harness/context_manager.py", line 364, in __enter__
    self.exec(cmd, shell=True)
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/site-packages/swebench/harness/context_manager.py", line 59, in __call__
    raise e
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/site-packages/swebench/harness/context_manager.py", line 51, in __call__
    output = subprocess.run(cmd, **combined_args)
File "/home/ubuntu/miniconda3/envs/swe-agent/lib/python3.9/subprocess.py", line 528, in run
    raise CalledProcessError(retcode, process.args,
subprocess.CalledProcessError: Command '. /home/ubuntu/SWE-agent/evaluation/testbed/predictions/sphinx-doc__sphinx/4.1/tmpe4u_b189/miniconda3/bin/activate 
sphinx-doc__sphinx__4.1 && conda install gxx_linux-64 gcc_linux-64 make -y' returned non-zero exit status 2.
"""
```
</details>


**2. Machine Discrepancies**: Different machines (e.g. x86, arm) require different miniconda installers. Consequently, on rare occasion, an installation script may work for one machine, but not for another. Currently, some task instances are not reproducible on arm64 machines due to missing dependencies. We thus recommend running evaluation on x86 machines.
- 🟡 Low (< 10)
- Affected Repositories: scikit-learn, sphinx, matplotlib
<details>
<summary>Click for Fix</summary>
To accommodate for the difference in installation between x86 and arch64 for scikit-learn, we added the `arch_specific_packages` field that allows us to specify what additional packages to install.

```python
"arch_specific_packages": {
    "aarch64": "gxx_linux-aarch64 gcc_linux-aarch64 make",
}
```

A clause in the `harness/context_manager.py` file then takes care of adding this installation to the conda commands.
</details>

**3. Which Conda?**: Even if the conda environment is created successfully, different conda versions will build the environment differently. For instance, we found that given the same installation instructions (e.g. `pip install numpy flask seaborn`), two different miniconda versions (e.g. `py38_23.11.0-1` and `py311_23.11.0-1`) will create environments that differ in the versions of installed pypi packages. As a result, newer conda versions might build environments differently than prior versions. The main implication of this is that PyPI packages are installed at different versions, which could then affect whether the repository is installed successfully + the behavior of the repository.
- 🟠 Medium (10+)
- Affected Repositories: django, sympy

<details>
<summary>Click for Fix</summary>
We write installation outputs per task instance to a log file. A log file will usually have the following kind of standard output written to it that describes which versions of libraries have been installed and included in the environment.

```bash
Requirement already satisfied: numpy!=1.24.0,>=1.17 in /n/fs/p-swe-bench/temp/seaborn/tmphkkamwwi/miniconda3/envs/mwaskom__seaborn__0.12/lib/python3.9/site-packages (from seaborn==0.12.2.dev0) (1.25.2)
Requirement already satisfied: pandas>=0.25 in /n/fs/p-swe-bench/temp/seaborn/tmphkkamwwi/miniconda3/envs/mwaskom__seaborn__0.12/lib/python3.9/site-packages (from seaborn==0.12.2.dev0) (2.1.0)
Requirement already satisfied: matplotlib!=3.6.1,>=3.1 in /n/fs/p-swe-bench/temp/seaborn/tmphkkamwwi/miniconda3/envs/mwaskom__seaborn__0.12/lib/python3.9/site-packages (from seaborn==0.12.2.dev0) (3.7.2)
Requirement already satisfied: pytest in /n/fs/p-swe-bench/temp/seaborn/tmphkkamwwi/miniconda3/envs/mwaskom__seaborn__0.12/lib/python3.9/site-packages (from seaborn==0.12.2.dev0) (7.4.1)
```

Over time, the version number may increase. The solution we use for this is to explicitly specify versions for PyPI packages that are installed (e.g. `click==8.0.1`).
Examples of this can be found throughout the `swebench/harness/constants.py` file, such as [here](https://github.com/princeton-nlp/SWE-bench/blob/main/swebench/harness/constants.py#L32).
</details>

**4. PyPI Package Dependency Updates**: Assuming failure modes #1, #2, and #3 don't occur (conda environment is created + is set up correctly), a last source of potential error is that the PyPI packages for dependencies is updated by the maintainers. At this time, based on the extent of our investigation, this is not a source of error for any task instances. However, if future versions of a PyPI package break prior functionality, this may cause an error.
- 🟠 Medium (10+)
- Affected Repositories: flask, requests, sphinx

The fix shown for Failure Mode #3 also resolves this situation.

**5. P2P Tests with Machine-Specific Paths**: We found that some P2P tests collected automatically via the harness picked up on tests with machine-specific paths to local testing files (e.g. a test named `test-validation.py:[/n/fs/p-swe-bench/temp/pytest-tmpdir/TEXT_001.txt]`), which are impossible to resolve on other machines. To remedy this, we have either 1. Rewritten the log parsing logic to refactor machine-specific paths into just keeping the file name (see [here](https://github.com/princeton-nlp/SWE-bench/blob/main/swebench/metrics/log_parsers.py#L28)), or 2. Removed these tests entirely.
- 🟡 Low (< 10)
- Affected Repositories: requests, sympy

## Investigation
To identify and then fix these issues, we carried out the following steps:
* Updated the logging mechanism for the harness to record not just task instance logs, but also testbed logging. This way, a history of how a conda environment is created + whether it installed is recorded, enabling easier debugging in the future.
* Re-ran task instance validation with a sweep across all Miniconda links between March 2023 and February 2024. We do this to "search" for which conda installation(s) correctly recreate the execution environments.
* Based on testbed logs, we manually + automatically identify cases fitting failure modes 1-4 and address them in a variety of ways:
    * Fixing the conda version to `py39_23.10.0-1`, which minor exceptions.
    * Adding `arch_specific_packages` to specify additional packages that must be installed for arch machines.
    * Made modifications as needed to pypi package versioning in the installation specifications.
* Based on task instance level logs, we identified discrepancies in logs stemming from later PyPI package updates, then modified the `pip` installation logic + configurations to cap or specify the version of specific libraries (e.g. `Jinja2<3.0`).
* Perform multiple rounds of validation to ensure that the fixes are effective, that the harness is working as expected, and that each task instance's P2P tests are relevant and reflective of prior behavior.
* Re-ran evaluation for the SWE-bench baselines ([BM25-13k, Oracle, Oracle-Greedy] + [Claude 2, ChatGPT 3.5]) as a sanity check to determine if the original numbers are still reproducible.

> The majority of our recovery efforts took place on an x86 machine. We also made efforts to reflect these changes on arm machines. We have included support for other architectures, but have *not* entirely verified them.

## Included Files
* `sweep_conda_links.py`: This script is used to sweep through a list of conda links and run the evaluation script on each one. It is used to generate evaluation logs per conda version.
* `updated_swe_bench.ipynb`: This script is used to identify which conda version is best for each repo/version pair.
* `check_harness.ipynb`: This is the script used to create the `check_harness.jsonl` file.

To perform multiple rounds of validation, we run the `sweep_conda_links.py` script multiple times. We use manual inspection + several on the fly scripts to identify, then rename or remove any problematic tests.

## Outcomes
We introduce the following fixes that are solutions to the discussed problems, which is generally starting from [#65](https://github.com/princeton-nlp/SWE-bench/pull/65) to the latest `1.0.x` releases:
* Fix conda version to `py39_23.10.0-1`.
* Specify specific pip package versions to install (e.g. `contourpy==1.1.0`).
* Add missing pip packages that need to be installed due to changes in the conda resolution logic.
* Add logic that cleans up + enforces versioning for `requirements.txt` and `environment.yml` based installation.
* Remove `shell=True` from the majority of `subprocess.run` calls to avoid local machine settings potentially interfering with the call.
* Re-run validation to re-verify the F2P and P2P tests for every task instance.
* Release the `check_harness.jsonl` file, which is a file of 126 gold predictions (one per unique repo/version) you can run to verify that your harness is working (all instances should pass).

We also found that:
* The original baseline numbers are reproduced entirely. The predictions and execution logs for these runs can be found on the SWE-bench [website](https://swe-bench.github.io/).
* Due to our repeated re-runs of validation, we were able to identify filtered out any P2P tests that are irrelevant or have machine specific paths.

Our diagnosis is that:
* Failure mode #1 should be *resolved*. We no longer rely on `latest`, in favor of set, prior versions of miniconda.
* Failure mode #2 should be *resolved* for x86 machines.
* Failure mode #3 should be *resolved*. Same reason as #1 + we ran a sweep across all miniconda versions to identify the one that reproduces all task instances correctly, which was `py39_23.10.0-1`.
* Failure mode #4 should be *resolved for now*. We have not specified PyPI package versions exhaustively in the installation specifications for all repo/version pairs. In the future, it is possible that later versions of dependencies cause issues. The permanent solution to this problem is to specify an explicit version for all pypi packages included in the installation specifications (defined in `swebench/harness/constants.py`).
* Failure mode #5 should be *resolved*. We have either removed or refactored the tests that have machine-specific paths.

## Remaining Problems
* While the explicit python versioning works for `x86` machines, we note that we have observed sporadic failing installation issues for different machines. Our plan is to continue to monitor this as reported by GitHub issues and make adjustments as needed.
* There are three task instances that have not been successfully reproduced at this time. We are actively working on resolving these three:
    * matplotlib__matplotlib-26399
    * sympy__sympy-11818
    * sympy__sympy-13865

## Future Steps
* We will move to a `Dockerfile` based solution to make evaluation machine-agnostic.
* We are continuing to explore how to make installation specifications more explicitly, robust, and reliable.

## Deliverables
* Please use `swebench>=1.1.0`.
* Use the `check_harness.jsonl` file to verify that your harness is working correctly.

✍️ Carlos & John