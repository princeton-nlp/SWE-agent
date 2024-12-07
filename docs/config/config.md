# Configuration

!!! warning "Under construction"
    This section is under construction. SWE-agent 1.0.0 is much more flexible, but that also means that we need to cover more ground here.

This page contains details describing how to write your own configurations to control how agents can interact with the `SWEEnv` environment.

A configuration is represented in one or more `.yaml` files, specified by the `--config` flag in the [command line interface](../usage/cl_tutorial.md), allowing you to...

* Define the **commands** that agents may use to traverse + modify a codebase (see [here](tools.md) for more details)
* Write **prompts** that are deterministically/conditionally shown to the agent over the course of a single trajectory.
* Control the **input/output interface** that sits between the agent and `SWEEnv`.

!!! tip "Default config files"
    Our default config files are in the [`config/`](https://github.com/SWE-agent/SWE-agent/tree/main/config) directory.

## Example configuration

This is the current default:

<details>
<summary><code>default_from_url.yaml</code></summary>

```yaml title="config/default_from_url.yaml"
--8<-- "config/default_from_url.yaml"
```
</details>

!!! hint "Relative paths"
    Relative paths in config files are resolved to the `SWE_AGENT_CONFIG_ROOT` environment variable (if set)
    or the SWE-agent repository root.

