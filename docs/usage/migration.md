## SWE-agent 1.0.0 migration guide

Welcome to the new SWE-agent! Everything has changed -- hopefully for the better!

If you're familiar with the old SWE-agent, here are the main changes you need to be aware of

## Command line interface and basic configuration

* Instead of the `run.py` script, we now have a central `sweagent` entry point that you can call after installing the package.
  This should be much more convenient!
* Instead of one `run.py` command, we now have several subcommands: `sweagent run` to run over single issues, `sweagent run-batch` to run over a whole batch of issues, and various utility commands. Run `sweagent --help` to see all options. Splitting up both commands made it easier to make both use cases more convenient and flexible.
* We have switched to a hierarchical configuration system. This means that command line options look something like this: `--agent.model.name=gpt-4o`.
  The configuration files have also been updated to reflect this.

## More advanced configuration

* Tools now live in tool bundles in the `tools/` directory. You can mix and match tools to your liking.

## Code

The codebase has been nearly rewritten from scratch and both more powerful and more flexible.

* The biggest change is [SWE-ReX](https://github.com/swe-agent/SWE-ReX), our new "backend" that handles all code execution.
* As a result of this, the `SWEEnv` class is basically gone and only is a small wrapper around a `swerex` runtime
* The `Agent` class also has gotten a lot simpler. It also delegates a lot of tool/execution logic to the new `Tools` class.
