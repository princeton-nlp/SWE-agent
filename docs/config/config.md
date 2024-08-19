# Configuration

This page contains details describing how to write your own configurations to control how agents can interact with the `SWEEnv` environment.

A configuration is represented as a single `.yaml` file, specified by the `--config` flag in the [command line interface](../usage/cl_tutorial.md), allowing you to...

* Define the **commands** that agents may use to traverse + modify a codebase (see [here](commands.md) for more details)
* Write **prompts** that are deterministically/conditionally shown to the agent over the course of a single trajectory.
* Control the **input/output interface** that sits between the agent and `SWEEnv`.

!!! tip "Default config files"
    Our default config files are in the [`config/`](https://github.com/princeton-nlp/SWE-agent/tree/main/config) directory.

## Configuration File Fields

The configuration is a `.yaml` file that consists of several fields. They are fully represented in this following outline:

```yaml
# Prompt Templates: Control how observations of environment are shown to agent
system_template: | # .yaml syntax for multi-line string value
  First `system` message shown to agent
instance_template: |- # .yaml syntax for multi-line string value w/ no new line
  Instance prompt, contains task instance-specific content
next_step_template: |-
  Format template of per-turn observation (Contains standard output from agent's action)
next_step_no_output_template: |-
  Format template of observation when there is no standard output from the agent's action
format_error_template: |-
  Format template of error message (Used when agent's action causes an error)
demonstration_template: |
  Format template for showing a demonstration to the agent
demonstrations:
- `trajectories/<username>/<experiment folder>/*.traj`
- File is a demonstration of how to solve a task. This could an agent generated trajectory.
- You can include 1+ demonstrations

# Environment States: Define features of the SWEEnv environment
env_variables:
# Default variables for SWEEnv at the beginning of each instance
  CURRENT_FILE: 0
  CURRENT_LINE:
  OVERLAP:
  SEARCH_FILES:
  SEARCH_INDEX:
  SEARCH_RESULTS:
  WINDOW_SIZE:
  START_INDEX:
  END_INDEX:
  START_CURSOR:
  END_CUROSR:
  START_CURSORS_MARK:
  END_CURSOR_MARK:
state_command: |
# `state_command` allows you to update state variables to reflect any aspect of the environment (e.g. current working directory)
  name: state
  code: |
    state() { echo '{"pwd": "'$PWD'"}';

# Action Interface: Define how an agent interacts with the SWEEnv environment
command_files:
- path/to/bash_file.sh
- Each file contains a list of commands implemented in bash
- You can include 1+ command files
parse_command: Reference to functionality for defining command documentation
history_processor: Reference to functionality for controlling agent's message history
parse_function: Parser run on agent output
```

In the [`config/`](https://github.com/princeton-nlp/SWE-agent/tree/main/config) directory, we recommend looking at...

* [`configs/`](https://github.com/princeton-nlp/SWE-agent/tree/main/config/configs) for examples of properly formatted configuration files. Each configuration differs in its set of commands, input/output format, demonstrations, etc.
* [`commands/`](https://github.com/princeton-nlp/SWE-agent/tree/main/config/commands) for the bash implementations of the custom commands that SWE-agent uses to navigate + edit the codebase. More information [here](commands.md).

!!! hint "Relative paths"
    Relative paths in config files are resolved to the `SWE_AGENT_CONFIG_ROOT` environment variable (if set)
    or the SWE-agent repository root.

<details>
<summary><code>default_from_url.yaml</code></summary>

```yaml
--8<-- "config/default_from_url.yaml"
```
</details>

## How a Configuration File is Processed
Some notes on processing that occurs on config fields when SWE-agent is run:

* Commands specified in `command_files` will be parsed into a single block of documentation text that can be referenced as `{command_docs}`.
* `env_variables` are the default variables for the bash environment at the beginning of each instance.
* `state_command` is used to extract state information from the bash environment (formatted as json) to be used in the templates given to the agent.

Possible variables that can be used in templates are:
- `{command_docs}` (an automatically compiled collection of available commands + their docstrings)
- any variable given in `env_variables` (same spelling), e.g., `{WINDOW_SIZE}`
- any variable extracted as json as part of the `state_command` function
- the last observation `{observation}`
- ... this list will grow as we implement more features!

## Template Workflow
The following diagram illustrates where each template is shown within a single episode of solving one task instance.

![template workflow](../assets/template_workflow.png)

One of three templates can be shown per turn:

* "Next Step" (`next_step_template`): Displayed if the model's action successfully runs. The output and a prompt for the next action is shown
* "Next Step (No Output)" (`next_step_no_output_template`): Displayed if the model's action successfully runs, but does not produce any standard output (e.g. `rm`, `cd`)
* "Format Error" (`format_error_template`): Displayed if the model's response is malformed. Over the next two turns...
  * If one of the model's next response is correct, the message history is updated such that the "Format Error" turn is not kept. The episode continues.
  * If the model's next two responses are both malformed, the episode terminates.

{% include-markdown "../_footer.md" %}