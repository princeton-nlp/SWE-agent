# Changing the demonstrations

An important way to show LMs how to use commands and interact with the environment is through providing a demonstration - which is basically a completed [trajectory](../usage/trajectories.md) that the LM can learn from.

For simplicity we only ingest demonstrations in the form of a trajectory file. However, since trajectory files are usually JSON, you can convert them to yaml using the `make_demos/convert_traj_to_demo.py` script to be more human-readable and easier to edit.

Demo (yaml) files are stored in the `make_demos/demos` directory by default and consist primarily of the sequence of actions that an LM would need to take to complete a task. It's important that your demo have the proper format to be parsed by SWE-agent and your config.

## Manually creating a custom trajectory <a name="manual"></a>

You can manually generate a trajectory by running the agent with `--model_name human_thought`.
This lets you input, at each turn, the thought (ending with END_THOUGHT) and then the action (a single command).

You should then convert that trajectory into a demonstration as shown below.

To edit text in `human_thought` mode:

1. Run the command `edit edit_start_line:edit_end_line`
2. Write the text you want to insert. Feel free to write the text across multiple lines.
3. Press `return` then write `end_of_edit` and then press `return` again to submit the edit.

If you would like to run `human_thought` mode without having to type in a thought at each turn (for debugging for example), use  `--model_name human`.

## Converting an existing trajectory into a demonstration

Here's how you can make a demo from an existing trajectory file (like the one created from the previous step):

1. Find a basic trajectory that you already like and want to use as the basis for your demo.
   For instance, consider the `.traj` files in the [`trajectories/demonstrations/` folder](https://github.com/princeton-nlp/SWE-agent/tree/main/trajectories/demonstrations)
   or find the trajectory from the previous step (the path will be printed at the bottom).
2. Run `python convert_traj_to_demo.py <path to trajectory file.traj>` to convert the trajectory to a demo.
   This demo will be saved as a readable yaml file in the `make_demos/demos` directory.
3. Edit the demo by hand to make it work for your particular use case and configuration.
4. (Optional) Run `python run_replay.py --traj_path <path to demo> --config_file <path to config file>` to execute the actions of the demo, have the system generate the execution output, and ensure that it works as expected.
5. Inspect the resulting trajectory to ensure it was executed correctly.
6. Specify the path to your demonstration in your [config file](config.md)

{% include-markdown "../_footer.md" %}
