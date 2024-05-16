# Inspector
We provide a web interface for visualizing `.traj` files from the `trajectories` folder more easily.

**Set Up**
* Run `python server.py --directory insert_full_absolute_path_to_the_trajectories_folder_here/trajectories`
* Open http://localhost:8000 in your browser to use the inspector.

**Additional flags**
- `--data_path`: Path to SWE-bench style dataset that trajectories were generated for (Optional)
- `--directory`: Directory of trajectories to inspect (Defaults to `./trajectories` folder)
- `--port`: Port to host web app (Defaults to `8000`).

**Example Usage**

From running the command:
```
python server.py --directory /Users/ofirp/swe-agent/trajectories
```
The inspector will then be launched in the browser:

<p align="center">
    <img src="../assets/inspector.png" alt="swe-agent.com" />
</p>
