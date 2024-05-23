# Modifying the behavior of SWE-agent

## Changing prompts and other configuration

The easiest way to modify the behavior of SWE-agent is to change prompts and similar settings.
This can be done using the config files. See [here](config.md) for more information.

## Changing the demonstrations

Any [trajectory](../usage/trajectories.md) can be turned into a new demonstrations. See [here](demonstrations.md) for how it's done.

## Code structure

* See the [`scripts/`](https://github.com/princeton-nlp/SWE-agent/tree/main/scripts/) folder for other useful scripts and details.
* See the [`config/`](https://github.com/princeton-nlp/SWE-agent/tree/main/config/) folder for details about how you can define your own configuration!
* See the [`sweagent/agent/`](https://github.com/princeton-nlp/SWE-agent/tree/main/sweagent/agent/) folder for details about the logic behind configuration based workflows.
* See the [`sweagent/environment/`](https://github.com/princeton-nlp/SWE-agent/tree/main/sweagent/environment/) folder for details about the `SWEEnv` environment (interface + implementation).
* See the [`trajectories/`](https://github.com/princeton-nlp/SWE-agent/tree/main/trajectories) folder for details about the output of `run.py`.
* See the [`evaluation/`](https://github.com/princeton-nlp/SWE-agent/tree/main/evaluation/) folder for details about how evaluation works.