# Command line usage tutorial

This tutorial walks you trough running SWE-agent from the command line.
Beginners might also be interested in the our web-based GUI (see [here](web_ui.md)).
This tutorial focuses on using SWE-agent as a tool to solve individual issues.
Benchmarking SWE-agent is covered [separately](benchmarking.md).

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

Here, 

* `--model_name` sets the language model that is used by SWE-agent (with `gpt4` being the default). More information on the available models in our [FAQ](faq.md)
* `--data_path` points to the source of the *problem statement* (for example, the GitHub issue that you want to solve). You can also point it to local files (see [below](#specifying-the-repository))
* `--config_file` includes settings such as the prompts. Changing the config file is the easiest way to get started with modifying SWE-agent (more advanced options are discussed [here](../dev/config.md)).
* `--per_instance_cost_limit` limits the total inference cost to $2 (default is $3).

!!! tip "All options"
    Run `python run.py --help` to see all available options for `run.py`. This tutorial will only cover a subset of options.

!!! tip "Running more than once"
    * The complete details of the run are saved as a "trajectory" file (more about them [here](trajectories.md)). They can also be turned into new [demonstrations](../dev/modify.md).
    * If you run the same command more than once, you will find that SWE-agent aborts with ` Skipping existing trajectory`. You can either remove the trajectory from the warning message, or add the `--skip_existing=False` flag.


## Specifying the repository

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

## Installing dependencies and setting up the environment

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

Let's take a look at the config file

```yaml
python: '3.10'
install: 'pip install -e .'
```

Here, `install` is an arbitrary command that is run, while `python` will be the python version that is setup with conda.

The config file also provides two more top level directives:

* `packages`: Path to a `requirements.txt` or to a `env.yml` as readable by conda
* `pip_packages`: A list of python packages that are installed with `pip install PACKAGE`

## Taking actions

* As mentioned [above](#specifying-the-repository), you can use `--apply_patch_locally` to have SWE-agent apply successful solution attempts to local files.
* Alternatively, when running on a GitHub issue, you can have the agent automatically open a PR if the issue has been solved by supplying the `--open_pr` flag. 
  Please use this feature responsibly (on your own repositories or after careful consideration).

Alternatively, you can always retrieve the patch that was generated by SWE-agent. 
Watch out for the followoing message in the log:


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