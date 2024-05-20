# Modifying the behavior of SWE-agent

## Changing prompts and other configuration

The easiest way to modify the behavior of SWE-agent is to change prompts and similar settings.
This can be done using the config files. See [here](config.md) for more information.

## Changing the demonstrations

If you'd like to modify the example demonstration that we feed the model at the start of each run, first generate a trajectory manually by running the agent with ```--model_name human``` 
and then convert that trajectory into a demonstration by following the guide [here](https://github.com/princeton-nlp/SWE-agent/tree/main/make_demos). 

To edit text in ```human``` mode:

1. Run the command ```edit edit_start_line:edit_end_line```
2. Write the text you want to insert. Feel free to write the text across multiple lines. 
3. Press ```return``` then write ```end_of_edit``` and then press ```return``` again to submit the edit.

## Code structure

* See the [`scripts/`](https://github.com/princeton-nlp/SWE-agent/tree/main/scripts/) folder for other useful scripts and details.
* See the [`config/`](https://github.com/princeton-nlp/SWE-agent/tree/main/config/) folder for details about how you can define your own configuration!
* See the [`sweagent/agent/`](https://github.com/princeton-nlp/SWE-agent/tree/main/sweagent/agent/) folder for details about the logic behind configuration based workflows.
* See the [`sweagent/environment/`](https://github.com/princeton-nlp/SWE-agent/tree/main/sweagent/environment/) folder for details about the `SWEEnv` environment (interface + implementation).
* See the [`trajectories/`](https://github.com/princeton-nlp/SWE-agent/tree/main/trajectories) folder for details about the output of `run.py`.
* See the [`evaluation/`](https://github.com/princeton-nlp/SWE-agent/tree/main/evaluation/) folder for details about how evaluation works.
