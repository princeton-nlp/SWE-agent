# Command line usage tutorial

This tutorial walks you through running SWE-agent from the command line.
Beginners might also be interested in the our web-based GUI (see [here](web_ui.md)).
This tutorial focuses on using SWE-agent as a tool to solve individual issues.
Benchmarking SWE-agent is covered [separately](benchmarking.md).
Finally, we have a different tutorial for using SWE-agent for [coding challenges](coding_challenges.md).

## Getting started

For the CLI, use the `run.py` script.
Let's start with an absolutely trivial example and solve an issue about a simple syntax error ([`swe-agent/test-repo #1`](https://github.com/SWE-agent/test-repo/issues/1))

```bash
python run.py \
  --model_name gpt4 \
  --data_path https://github.com/SWE-agent/test-repo/issues/1 \
  --config_file config/default_from_url.yaml \
  --per_instance_cost_limit 2.00
```

<details>
<summary>Output</summary>

```json
--8<-- "docs/usage/cl_tutorial_cmd_1_output.log"
```
</details>

Here,

* `--model_name` sets the language model that is used by SWE-agent (with `gpt4` being the default). More information on the available models in our [FAQ](usage_faq.md)
* `--data_path` points to the source of the *problem statement* (for example, the GitHub issue that you want to solve). You can also point it to local files (see [below](#specifying-the-repository))
* `--config_file` includes settings such as the prompts. Changing the config file is the easiest way to get started with modifying SWE-agent (more advanced options are discussed [here](../config/config.md)).
* `--per_instance_cost_limit` limits the total inference cost to $2 (default is $3).

!!! tip "All options"
    Run `python run.py --help` to see all available options for `run.py`. This tutorial will only cover a subset of options.

!!! tip "Running more than once"
    * The complete details of the run are saved as a "trajectory" file (more about them [here](trajectories.md)). They can also be turned into new [demonstrations](../config/demonstrations.md).
    * If you run the same command more than once, you will find that SWE-agent aborts with ` Skipping existing trajectory`. You can either remove the trajectory from the warning message, or add the `--skip_existing=False` flag.
    * If you solve multiple issues from the same repository/in the same environment, you can specify the
      `--cache_task_images` flag. This will create a persistent docker image with the initialized environment
      required for the problem.


## Specifying the repository

!!! note "Operating in batch mode: Running on SWE-bench and other benchmark sets"
    If you want to run SWE-agent in batch mode on SWE-bench or another whole evaluation set, see
    [benchmarking](benchmarking.md). This tutorial focuses on using SWE-agent on
    individual issues.

In the above example, the repository/codebase is inferred from the `--data_path`.
This options is currently only available for GitHub issues.
For all other use cases, you can specify `--repo_path`, which accepts either GitHub
URLs or paths to local repositories.

To try it out, let's clone the test repository from the previous section.

```bash
git clone git@github.com:SWE-agent/test-repo.git
```

and then run

```bash hl_lines="2 3 5"
python run.py \
  --data_path /path/to/test-repo/problem_statements/1.md \
  --repo_path /path/to/test-repo \
  --config_file config/default_from_url.yaml \
  --apply_patch_locally
```

where you replaced paths with the prefix `/path/to/.../` with the actual paths to the corresponding file/directory.

We have also added a new flag, `--apply_patch_locally`, which will make SWE-agent apply the changes to the local repository (if it believes that it has successfully solved the issue).

You can mix and match the different ways of specifying problem statements and repositories. For example, any of the following combination of options also works

* Local problem statement with GitHub repository (`--data_path /path/to/problem.md --repo_path https://github.com/...`): Let SWE-agent work on something that wasn't reported yet
* GitHub issue with local repository (`--data_path https://github.com/.../issues/.. --repo_path /path/to/... --apply_patch_locally`): Let SWE-agent solve a GitHub issue locally (for example to edit the solution afterwards)
* GitHub issue with different GitHub repository: Useful with the `--open_pr` flag (see [below](#taking-actions)) when working from a fork.

In addition, if `--repo_path` points to a GitHub repository, you can use `--base_commit` to specify

* A branch name (e.g., `dev`),
* A tag (e.g., `v1.0.0`),
* A commit hash (e.g., `a4464baca1f28d7733337df6e4daa6c1ed920336`).

SWE-agent will then start from this commit when trying to solve the problem.

!!! warning "Uncommitted changes"
    When running with a local `--repo_path`, SWE-agent will use the last commit, i.e., all local, uncommitted changes will not be seen by SWE-agent.

## Installing dependencies and setting up the environment <a name="environment-setup"></a>

Now let's move on to a slightly more complicated issue ([`swe-agent/test-repo #22`](https://github.com/SWE-agent/test-repo/issues/22)).

What makes it more complicated? This time the problematic code is part of a library `testpkg`, so SWE-agent first has to install the package in order to reproduce the issue before searching for the problematic code.

In most circumstances, GPT4 will attempt to install the package and requirements (usually with some form of `pip install .` or `pip install pkg`). However, this wastes valuable queries to the LM. In addition, you might need to run your software for a specific python version or have other specific environment settings. The `--environment_setup` flag is used to fix this problem.

Let's try it:

```bash hl_lines="4"
python run.py \
  --data_path https://github.com/SWE-agent/test-repo/issues/22 \
  --config_file config/default_from_url.yaml \
  --environment_setup config/environment_setup/py310_default.yaml
```

This time, `pip install -e .` is called before SWE-agent gets to work, installing the package defined in the repository.

Let's take a look at the `py310_default.yaml` config file

REMOVED OUTDATED

Here, `install` is an arbitrary command that is run, while `python` will be the required python version.
The default install command will create an [editable install][] of the python package.
We first try to use [`uv pip`][uv] (a much faster implementation of `pip` in [rust][]), but fall back to "normal" pip if it fails.

!!! tip "Editable installs"
    Using [editable installs][editable install] is crucial for SWE-agent so that
    changes to the package code take effect without having to reinstall the package.

[editable install]: https://setuptools.pypa.io/en/latest/userguide/development_mode.html
[uv]: https://pypi.org/project/uv/
[rust]: https://www.rust-lang.org/

The config file can have the following keys:

* `python`: Python version (will be set up via conda)
* `packages`: Either `requirements.txt`, `environment.yml` (finds the corresponding file and installs from there) or a whitespace separated list of conda packages
* `pip_packages`: A list of additional python packages that are installed with `pip install PACKAGE`
* `pre_install`: A list of custom commands
* `install`: A custom command
* `post_install`: A list of custom commands

Instead of the `setup.yaml` file, you can also directly specify the path to a shell script, e.g., `--environment_setup /path/to/setup.sh`.
If you have very specific requirements, that can _not_ be installed via conda, you can [create a custom Docker image](../config/docker.md).

### Installing non-python dependencies

While SWE-agent has so far only been benchmarked and optimized for python project, you can still use it on repositories of any language.

In most cases, this means creating a [custom Docker image](../config/docker.md). However, you can for example install node dependencies with
`--environment_setup setup.sh`, where `setup.sh` looks as follows:

```bash
apt-get update
yes|apt-get install curl
yes|curl -L https://bit.ly/n-install | bash
/root/n/bin/n latest
npm install
```

However, this will take some time, so make sure to cache the environment (see the next section) or create a [custom Docker image](../config/docker.md).

## Speeding up SWE-agent <a name="speedup"></a>

!!! tip "Speed up in v0.6"
    SWE-agent v0.6 (June 4th, 2024) introduced major speedups. Please upgrade to the latest version.
    To make use of [`uv pip`][uv], make sure that you have the latest `sweagent/swe-agent:latest` image.

After the Docker container has been started, the target repository cloned/copied, and the dependencies installed,
almost all of the remaining runtime can be attributed to waiting for your LM provider to answer your API calls.

Therefore, speeding SWE-agent is mostly about speeding up the setup stages.
We currently offer three ways to cache the setup stages:

* By specifying `--container_name`, you run SWE-agent with a _persistent_ Docker container: Rather than being deleted
  after every task, the Docker container will only be paused and can be resumed. Cloned repositories from previous
  runs with the same container name, as well as any installed conda environments (versioned by the version of the package
  you are installing) will be already available.
* Alternatively, you can specify `--cache_task_images`. For every repository/base commit/environment setup, we
  [commit][docker commit] the changes from the installation stage to the Docker image. The corresponding containers are temporary as usual.
  Unlike the persistent containers, there will be a new image _for almost every base commit_ (that is, probably for every task
  when evaluating on a benchmark), which makes this only relevant when running over the same tasks more than once
  (for example when testing different agent configurations or LMs).
* You can also [build your own Docker image](../config/docker.md) and ensure that all relevant conda environments and repositories
  are available (check the logs from the previous runs to get the names for repositories and environments).

!!! tip "Confused about the two options?"
    Probably `--container_name my_container_name` will do what you want.

!!! note "What's the difference between Docker images and containers?"
    Docker containers are running instances of Docker images (that you can think of as snapshots of what
    happens after you build the `Dockerfile`). [More information](https://stackoverflow.com/a/26960888/).

[docker commit]: https://docs.docker.com/reference/cli/docker/container/commit/

## Taking actions

* As mentioned [above](#specifying-the-repository), you can use `--apply_patch_locally` to have SWE-agent apply successful solution attempts to local files.
* Alternatively, when running on a GitHub issue, you can have the agent automatically open a PR if the issue has been solved by supplying the `--open_pr` flag.
  Please use this feature responsibly (on your own repositories or after careful consideration).

Alternatively, you can always retrieve the patch that was generated by SWE-agent.
Watch out for the following message in the log:


```
╭──────────────────────────── 🎉 Submission successful 🎉 ────────────────────────────╮
│ SWE-agent has produced a patch that it believes will solve the issue you submitted! │
│ Use the code snippet below to inspect or apply it!                                  │
╰─────────────────────────────────────────────────────────────────────────────────────╯
```

And follow the instructions below it:

```bash
 # The patch has been saved to your local filesystem at:
 PATCH_FILE_PATH='/Users/.../patches/05917d.patch'
 # Inspect it:
 cat "${PATCH_FILE_PATH}"
 # Apply it to a local repository:
 cd <your local repo root>
 git apply "${PATCH_FILE_PATH}"
```

{% include-markdown "../_footer.md" %}
