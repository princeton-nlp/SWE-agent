# Modifying the behavior of SWE-agent

## Code structure

* See the [`scripts/`](scripts/) folder for other useful scripts and details.
* See the [`config/`](config/) folder for details about how you can define your own configuration!
* See the [`sweagent/agent/`](sweagent/agent/) folder for details about the logic behind configuration based workflows.
* See the [`sweagent/environment/`](sweagent/environment/) folder for details about the `SWEEnv` environment (interface + implementation).
* See the [`trajectories/`](trajectories) folder for details about the output of `run.py`.

## Changing the demonstrations

If you'd like to modify the example demonstration that we feed the model at the start of each run, first generate a trajectory manually by running the agent with ```--model_name human``` 
and then convert that trajectory into a demonstration by following the guide [here](https://github.com/princeton-nlp/SWE-agent/tree/main/make_demos). 

To edit text in ```human``` mode:

1. Run the command ```edit edit_start_line:edit_end_line```
2. Write the text you want to insert. Feel free to write the text across multiple lines. 
3. Press ```return``` then write ```end_of_edit``` and then press ```return``` again to submit the edit.