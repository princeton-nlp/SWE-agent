# EnIGMA Tutorial

This tutorial walks you through running EnIGMA from the command-line.
It is based on basic knowledge of the command-line of SWE-agent that is covered [here](cl_tutorial.md).
This tutorial focuses on using EnIGMA as a tool to solve individual CTF challenges.

## Getting started


For the CLI, use the `run.py` script.
Let's start with an absolutely trivial example and solve a CTF challenge where the flag is leaked in its description.
We will first need to clone [NYU CTF benchmark](https://github.com/NYU-LLM-CTF/LLM_CTF_Database).

Then, assuming the following directory structure:

```
├── SWE-agent
│ ├── run.py
│ └── ...
├── LLM_CTF_Database
│ ├── 2017
│ ├── 2018
│ ├── 2019
└ └── ...
```

We will run the following command,

```bash
python run.py \
  --model_name gpt4 \
  --image_name sweagent/enigma:latest \
  --data_path ../LLM_CTF_Database/2018/CSAW-Finals/misc/leaked_flag/challenge.json \
  --repo_path ../LLM_CTF_Database/2018/CSAW-Finals/misc/leaked_flag \
  --config_file config/default_ctf.yaml \
  --per_instance_cost_limit 2.00
```

<details>
<summary>Output</summary>

```json
--8<-- "docs/usage/enigma_cmd_output.log"
```
</details>

Here,

* `--model_name` sets the language model that is used by EnIGMA (with `gpt4` being the default). More information on the available models in our [FAQ](usage_faq.md)
* `--data_path` points to the **local** source of the *CTF challenge metadata* (see [below](#specifying-the-challenge))
* `--repo_path` points to the **local** source of the *CTF challenge files* (see [below](#specifying-the-challenge))
* `--config_file` includes settings such as the prompts. Changing the config file is the easiest way to get started with modifying EnIGMA (more advanced options are discussed [here](../config/config.md)).
* `--per_instance_cost_limit` limits the total inference cost to $2 (default is $3).

!!! tip "All options"
    Run `python run.py --help` to see all available options for `run.py`. This tutorial will only cover a subset of options.

!!! tip "Running more than once"
    * The complete details of the run are saved as a "trajectory" file (more about them [here](trajectories.md)). They can also be turned into new [demonstrations](../config/demonstrations.md).
    * If you run the same command more than once, you will find that SWE-agent aborts with ` Skipping existing trajectory`. You can either remove the trajectory from the warning message, or add the `--skip_existing=False` flag.
    * If you solve multiple challenges from the same in the same environment, you can specify the
      `--cache_task_images` flag. This will create a persistent docker image with the initialized environment
      required for the problem.

## Specifying the challenge

In the above example we used two arguments to specify the challenge, both of them are necessary to run EnIGMA:

* `--data_path` is the local source of the *CTF challenge metadata*, this is a file usually named `challenge.json` that has the following structure:
```json
{
    "name": "challenge name",
    "description": "challenge description",
    "category": "challenge category, for example crypto",
    "files": ["list of files to upload for this challenge"],
    "box": "optional URL for external server challenge",
    "internal_port": "optional port for external server challenge"
}
```
If a `docker-compose.yml` file exist in the directory of the challenge json file, this docker compose file will be initiated during the setup of the environment for the challenge. This feature is for challenges that has an external server dependency (such as web challenges that require web servers).
* `--repo_path` is the local source of the *CTF challenge files*. Any files needed for the challenge as specified in the challenge metadata file, will be uploaded relative to the repo path specified by this parameter. Usually, this will point to the directory containing the `challenge.json` file.

