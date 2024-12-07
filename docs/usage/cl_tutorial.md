# Command line basics

!!! abstract "Command line basics"
    This tutorial walks you through running SWE-agent from the command line.

    * Please read our [hello world](hello_world.md) tutorial before proceeding.
    * This tutorial focuses on using SWE-agent as a tool to solve individual issues.
      Benchmarking SWE-agent is covered [separately](benchmarking.md).
      Finally, we have a different tutorial for using SWE-agent for [coding challenges](coding_challenges.md).

## A few examples

Before we start with a more structured explanation of the command line options, here are a few examples that you might find immediately useful:

```bash title="Fix a github issue"
python run.py \
  --agent.model.name=gpt4 \
  --agent.model.per_instance_cost_limit=2.00 \  # (1)!
  --env.repo.github_url=https://github.com/SWE-agent/test-repo \
  --problem_statement.github_url=https://github.com/SWE-agent/test-repo/issues/1
```

```bash title="Work on a github repo with a custom problem statement" hl_lines="4"
python run.py \
  ...
  --env.repo.github_url=https://github.com/SWE-agent/test-repo \
  --problem_statement.text="Hey, can you fix all the bugs?"
```

```bash title="Fix a bug in a local repository using a custom docker image" hl_lines="4 5 6"
git clone https://github.com/SWE-agent/test-repo.git
python run.py \
  --agent.model.name=claude-3.5 \  # (1)!
  --env.repo.path=test-repo \
  --problem_statement.path=test-repo/problem_statements/1.md \
  --env.deployment.image=python:3.12  # (2)!
```

1. Make sure to add anthropic keys to the environment for this one!
2. This points to the [dockerhub image](https://hub.docker.com/_/python) of the same name


For the next example, we will use a cloud-based execution environment instead of using local docker containers.
For this, you first need to set up a modal account, following the instructions at XXX

```bash title="Deployment on modal (cloud-based execution)" hl_lines="4"
python run.py \
  ...
  --env.deployment.type=modal \
  --env.deployment.image=python:3.12
```

!!! tip "All options"
    Run `python run.py --help` to see all available options for `run.py`. This tutorial will only cover a subset of options.

## Configuration basics

All configuration options can be specified either in one or more `.yaml` files, or as command line arguments. For example, our first command can be written as

=== "Command line"

    ```bash
    python run.py --config my_run.yaml
    ```

=== "Configuration file"

    ```yaml title="my_run.yaml"
    agent:
      model:
        name: gpt4
        per_instance_cost_limit: 2.00
    env:
      repo:
        github_url: https://github.com/SWE-agent/test-repo
    problem_statement:
      github_url: https://github.com/SWE-agent/test-repo/issues/1
    ```

But we can also split it up into multiple files and additional command line options:

=== "Command line"

    ```bash
    python run.py --config agent.yaml --config env.yaml \
        --problem_statement.text="Hey, can you fix all the bugs?"
    ```

=== "`agent.yaml`"

    ```yaml title="agent.yaml"
    agent:
      model:
        name: gpt4
        per_instance_cost_limit: 2.00
    ```

=== "`env.yaml`"

    ```yaml title="env.yaml"
    env:
      repo:
        github_url: https://github.com/SWE-agent/test-repo
    ```

The default config file is `config/default.yaml`. Let's take a look at it:

<details>
<summary>Example: default config <code>default.yaml</code></summary>

```yaml
--8<-- "config/default_from_url.yaml"
```
</details>

As you can see, this is where all the templates are defined!

This file is also loaded when no other `--config` options are specified.
So to make sure that we get the default templates in the above examples with `--config`, we should have added

```bash
--config config/default.yaml
```

in addition to all the other `--config` options for the two examples above.

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

REMOVED OUTDATED

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
