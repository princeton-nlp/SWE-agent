# Inspector
We provide a web interface for visualizing `.traj` files from the `trajectories` folder more easily.

**Set Up**
* Run `python server.py trajectories`
* Open http://localhost:8000 in your browser to use the inspector.

**Additional flags**
- `--data_path`: Path to SWE-bench style dataset that trajectories were generated for (Optional)
- `--directory`: Directory of trajectories to inspect (Defaults to `./trajectories` folder)
- `--port`: Port to host web app (Defaults to `8000`).

**Example Usage**

From running the command:
```
python server.py --directory trajectories/carlosejimenez/gpt-4-1106-preview__swe-bench-dev-40-seed24__default_sys-env_window100-detailed_cmd_format-full_history-1_demos__t-0.20__p-0.95__c-4.00__install-1__sweep-01-run-4
```
The inspector will then be launched in the browser:

<p align="center">
    <img src="../assets/inspector.png" alt="swe-agent.com" />
</p>
