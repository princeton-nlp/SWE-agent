# Make demos
An important way to show LMs how to use commands and interact with the environment is through providing a demonstration - which is basically a completed trajectory that the LM can learn from.

For simplicity we just ingest demonstrations in the from of a trajectory file. However, since trajectory files are usually JSON, you can convert them to yaml using the `convert_traj_to_demo.py` script to be more human-readable and easier to edit.

Demo (yaml) files are stored in the `make_demos/demos` directory by default and consist primarily of the sequence of actions that an LM would need to take to complete a task. It's important that your demo have the proper format to be parsed by SWE-agent and your config.s

Here's how you can make a demo:
1. Find a basic trajectory that you already like and want to use as the basis for your demo.
     - For instance, consider the `trajectories/demonstrations/replay__marshmallow-code__marshmallow-1867__default_sys-env_window100__t-0.20__p-0.95__c-2.00__install-1/marshmallow-code__marshmallow-1867.traj` trajectory for reference.
2. Run `python convert_traj_to_demo.py <path to trajectory file>` to convert the trajectory to a demo.
     - This demo will be saved as a readable yaml file in the `make_demos/demos` directory.
3. Edit the demo by hand to make it work for your particular use case and configuration.
4. Run `python run_replay.py --traj_path <path to demo> --config_file <path to config file>` to execute the actions of the demo, have the system generate the execution output, and ensure that it works as expected.
      - Protip: you can use `sweagent.run` with `--model_name human` to manually execute actions in the environment - useful for debugging.
5. Inspect the resulting trajectory to ensure it was executed correctly.