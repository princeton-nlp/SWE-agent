# SWE-agent 1.0.0 migration guide

!!! warning "Work in progress"
    We're currently in the process of updating this guide.

Welcome to SWE-agent 1.0! So much new stuff! Here's a quick rundown of the cool new things you can do:

* :sparkles: Fast, massively parallel code execution with [SWE-ReX](https://github.com/swe-agent/SWE-ReX).
* :sparkles: Run SWE-agent locally but execute code in the cloud (using modal, AWS, or anything else that runs [SWE-ReX](https://github.com/swe-agent/SWE-ReX)).
* :sparkles: Flexible tool definitions with [tool bundles](../config/tools.md).
* :sparkles: All language models supported using `litellm` (see [models](../installation/keys.md)).
* :sparkles: Override any configuration option from the command line (see [command line basics](../usage/cl_tutorial.md)).
* :sparkles: Greatly simplified and cleaned up codebase. In particular, the `Agent` class is now much easier to modify.

If you're familiar with the old SWE-agent, here are the main changes you need to be aware of.

## Command line interface and basic configuration

* Instead of the `run.py` script, we now have a central `sweagent` entry point that you can call after installing the package.
  This should be much more convenient!
* Instead of one `run.py` command, we now have several subcommands: `sweagent run` to run over single issues, `sweagent run-batch` to run over a whole batch of issues, and various utility commands. Run `sweagent --help` to see all options. Splitting up both commands made it easier to make both use cases more convenient and flexible.
* We have switched to a hierarchical configuration system. This means that command line options look something like this: `--agent.model.name=gpt-4o`.
  The configuration files have also been updated to reflect this.

## Environment setup

We removed the complicated mess of environment setup options (`conda` environments, `pip`, docker images, etc.).
Instead, you now always start from a docker image of your choice and we recommend that this should ship with all the dependencies you need.
However, you can also execute additional commands before starting the agent with `EnvironmentConfig.post_startup_commands`.
Additionally, every [tool bundle](../config/tools.md) can include a `setup.sh` script that will be executed, allowing to e.g., install `flake8` if needed by the tools.

## More advanced configuration

* Tools now live in tool bundles in the `tools/` directory. You can mix and match tools to your liking.

## Code

The codebase has been nearly rewritten from scratch and both more powerful and more flexible.

* The biggest change is [SWE-ReX](https://github.com/swe-agent/SWE-ReX), our new "backend" that handles all code execution.
* As a result of this, the `SWEEnv` class is basically gone and only is a small wrapper around a `swerex` runtime
* The `Agent` class also has gotten a lot simpler. It also delegates a lot of tool/execution logic to the new `Tools` class.
