# Trajectory inspector

We provide a web interface for visualizing [`.traj` files](trajectories.md) from the `trajectories` folder more easily.

**Example Usage**

Run the inspector in the current directory (this is where your `*.traj` files are):

```bash
sweagent inspector
```
The inspector will then be launched in the browser:

![trajectory inspector](../assets/inspector_1.png){: style="width: 49%;"}
![trajectory inspector](../assets/inspector_2.png){: style="width: 49%;"}

!!! tip
    If you do not see evaluation results, make sure that the SWE-bench output
    is called `results.json` and is in the same directory as the trajectories.

!!! tip
    To see gold patches, point `--data_path` to the SWE-bench dataset.

**Additional flags**

- `--directory`: Directory of trajectories to inspect (Defaults to current directory)
- `--port`: Port to host web app (Defaults to `8000`).

{% include-markdown "../_footer.md" %}
