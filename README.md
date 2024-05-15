<p align="center">
  <a href="https://www.swe-agent.com/">
    <img src="assets/swe-agent-banner.png" alt="swe-agent.com" />
  </a>
</p>


<p align="center">
  <a href="https://swe-agent.com"><strong>Website & Demo</strong></a>&nbsp; | &nbsp;
  <a href="https://discord.gg/AVEFbBn2rH"><strong>Discord</strong></a>&nbsp; | &nbsp;
  <a href="https://swe-agent.com/paper.pdf"><strong>Preprint</strong></a>
</p>


## 👋 Overview <a name="overview"></a>
SWE-agent turns LMs (e.g. GPT-4) into software engineering agents that can fix bugs and issues in real GitHub repositories.

On [SWE-bench](https://github.com/princeton-nlp/SWE-bench), SWE-agent resolves **12.29%** of issues, achieving the state-of-the-art performance on the full test set.

We accomplish our results by designing simple LM-centric commands and feedback formats to make it easier for the LM to browse the repository, view, edit and execute code files. We call this an 🤖 **Agent-Computer Interface (ACI)**.
Read more about it in our [paper](https://swe-agent.com/paper.pdf)!

SWE-agent is built and maintained by researchers from Princeton University. 

<p align="center">
  <img src="assets/results+preview.png" style="width: 80%; height: auto;">
</p>

If you found this work helpful, please consider using the following citation:
```
@misc{yang2024sweagent,
      title={SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering}, 
      author={John Yang and Carlos E. Jimenez and Alexander Wettig and Kilian Lieret and Shunyu Yao and Karthik Narasimhan and Ofir Press},
      year={2024},
}
```

### ✨ Use SWE-agent as a dev tool

We provide a command line tool and a graphical web interface:

![My Movie 3](https://github.com/princeton-nlp/SWE-agent/assets/13602468/fa201621-ec31-4644-b658-c1d0feb92253)

## 🚀 Installation <a name="setup"></a>

### ☁️ Run from your browser

<details>
<summary>🔎 Watch the video</summary>

https://github.com/princeton-nlp/SWE-agent/assets/13602468/44d60674-59ca-4986-9b22-7052a45cbed9
</details>

1. Click [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/princeton-nlp/SWE-agent)
2. Add your API keys to `keys.cfg` (find the file in the left sidebar and fill out the template)
3. Make sure to wait until the `postCreateCommand` in the terminal window at the bottom is finished
4. Enter your SWE-agent command ([see below](#real-life))

### Install from source

> [!WARNING]
> Expect some issues with Windows (we're working on them).
> In the meantime, use Docker (see below).

1. [Install Docker](https://docs.docker.com/engine/install/), then start Docker locally.
2. For the web interface only: Install [`nodejs`][nodejs-install].
3. Clone this repository.
4. Run `pip install --editable .` at the repository root (as with any python setup, it's recommended to use [conda][] or [virtual environments][] to manage dependencies).
5. Run `./setup.sh` to create the `swe-agent` docker image.
6. Create a `keys.cfg` file at the root of this repository ([see below](#tokens)).

[nodejs-install]: https://docs.npmjs.com/downloading-and-installing-node-js-and-npm

> [!TIP]
> If you run into docker issues, see the [installation issues section](#more-installation-tips) for more help

[conda]: https://docs.conda.io/en/latest/
[virtual environments]: https://realpython.com/python-virtual-environments-a-primer/

### Fallback: Run with docker

> [!warning]
> The latest containerized version does not yet provide the web interface.

Instead of installing SWE-agent from source, you can also run the software directly using Docker. 

1. [Install Docker](https://docs.docker.com/engine/install/), then start Docker locally.
2. Run `docker pull sweagent/swe-agent:latest`
3. Add your API tokens to a file `keys.cfg` as explained [below](#tokens)

Then run

```bash
# NOTE:
# This assumes that keys.cfg is in your current directory (else fix the path below)
# This command is equivalent to the script shown in the quickstart 
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/keys.cfg:/app/keys.cfg \
  sweagent/swe-agent-run:latest \
  python run.py --image_name=sweagent/swe-agent:latest \
  --model_name gpt4 \
  --data_path https://github.com/pvlib/pvlib-python/issues/1603 \
  --config_file config/default_from_url.yaml  --skip_existing=False
```

> [!TIP]
> * For more information on the different API keys/tokens, see [below](#tokens).
> * If you're using docker on Windows, use `-v //var/run/docker.sock:/var/run/docker.sock`
>   (double slash) to escape it ([more information](https://stackoverflow.com/a/47229180/)).
> * See the [installation issues section](#more-installation-tips) for more help if you run into
>   trouble.


### 🔑 Add your API keys/tokens <a name="tokens"></a>

Create a `keys.cfg` file at the root of this repository and populate it with your API keys.

```
GITHUB_TOKEN: 'GitHub Token Here (optional)'
OPENAI_API_KEY: 'OpenAI API Key Here if using OpenAI Model (optional)'
```

<details>
<summary>🔎 More options for different keys (click to unfold)</summary>

All keys are optional.

```
GITHUB_TOKEN: 'GitHub Token for access to private repos'  # <-- delete line if not used
OPENAI_API_KEY: 'OpenAI API Key Here if using OpenAI Model'
ANTHROPIC_API_KEY: 'Anthropic API Key Here if using Anthropic Model'
TOGETHER_API_KEY: 'Together API Key Here if using Together Model'
AZURE_OPENAI_API_KEY: 'Azure OpenAI API Key Here if using Azure OpenAI Model'
AZURE_OPENAI_ENDPOINT: 'Azure OpenAI Endpoint Here if using Azure OpenAI Model'
AZURE_OPENAI_DEPLOYMENT: 'Azure OpenAI Deployment Here if using Azure OpenAI Model'
AZURE_OPENAI_API_VERSION: 'Azure OpenAI API Version Here if using Azure OpenAI Model'
OPENAI_API_BASE_URL: 'LM base URL here if using Local or alternative api Endpoint'
```  
</details>

See the following links for tutorials on obtaining [Anthropic](https://docs.anthropic.com/claude/reference/getting-started-with-the-api), [OpenAI](https://platform.openai.com/docs/quickstart/step-2-set-up-your-api-key), and [Github](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) tokens.

### More installation tips <a name="more-installation-tips"></a>

If you seem to be having issues with running docker

* Make sure that you allow the use of the Docker socket. In Docker desktop, click *Settings* > *Advanced* > *Allow the default Docker socket to be used (requires password)*
* If your docker installation uses a different socket, you might have to symlink them, see [this command for example](https://github.com/princeton-nlp/SWE-agent/issues/20#issuecomment-2047506005)

Any remaining issues? Please [open a GitHub issue](https://github.com/princeton-nlp/SWE-agent/issues/new/choose)!

## 🔥 Solve real GitHub issues! <a name="real-life"></a>

To start our web UI, simply run

```bash
./start_web_ui.sh
```

If the user interface doesn't automatically open in your browser, please open it at `http://localhost:3000`.

Currently, the web interface only has a subset of the options of the command line interface (CLI). 
For the CLI, use the `run.py` script:

```bash
python run.py --model_name gpt4 \
  --data_path https://github.com/pvlib/pvlib-python/issues/1603 \
  --config_file config/default_from_url.yaml \
  --per_instance_cost_limit 2.00 
```

You can also apply to it to a local repository:

```bash
python run.py --model_name gpt4 \
  --data_path /path/to/my_issue.md \
  --repo_path /path/to/my/local/repo \
  --config_file config/default_from_url.yaml \
  --per_instance_cost_limit 2.00 \
  --apply_patch_locally
```

> [!TIP]
> * Run `python run.py --help` to see all available options.
> * You can have the agent automatically open a PR if the issue has been solved by supplying the `--open_pr`
>   flag. Please use this feature responsibly (on your own repositories or after careful consideration).

* See the [`scripts/`](scripts/) folder for other useful scripts and details.
* See the [`config/`](config/) folder for details about how you can define your own configuration!
* See the [`sweagent/agent/`](sweagent/agent/) folder for details about the logic behind configuration based workflows.
* See the [`sweagent/environment/`](sweagent/environment/) folder for details about the `SWEEnv` environment (interface + implementation).
* See the [`trajectories/`](trajectories) folder for details about the output of `run.py`.

<details>
<summary> Ollama Support</summary>

Models served with an ollama server can be used by specifying `--model` with `ollama:model_name` and `--host_url` to point to the url used to serve ollama (`http://localhost:11434` by default). See more details about using ollama [here](https://github.com/ollama/ollama/tree/main/docs).

```bash
python run.py --model_name ollama:deepseek-coder:6.7b-instruct \
  --host_url http://localhost:11434 \
  --data_path https://github.com/pvlib/pvlib-python/issues/1603 \
  --config_file config/default_from_url.yaml
```
</details>

## 💽 Benchmarking <a name="benchmarking"></a>

There are two steps to the SWE-agent pipeline. First SWE-agent takes an input GitHub issue and returns a pull request that attempts to fix it. We call that step *inference*. The second step (currently, only available for issues in the SWE-bench benchmark) is to *evaluate* the pull request to verify that it has indeed fixed the issue. 

> [!WARNING]
> At this moment, there are known issues with a small number of repositories that don't install properly for `arm64` / `aarch64` architecture computers. We're working on a fix, but if you'd like to run and evaluate on the entirety of SWE-bench, the easiest way is by using an `x86` machine.

### 👩‍💻 Inference <a name="inference"></a>
**Inference on *any* GitHub Issue**: See [above](#real-life).

**Inference on SWE-bench**: Run SWE-agent on [SWE-bench Lite](https://www.swebench.com/lite.html) and generate patches.
```bash
python run.py --model_name gpt4 \
  --per_instance_cost_limit 2.00 \
  --config_file ./config/default.yaml
```

If you'd like to run on a *single* issue from SWE-bench, use the `--instance_filter` option as follows:
```bash
python run.py --model_name gpt4 \
  --instance_filter marshmallow-code__marshmallow-1359
```

### 🧪 Evaluation <a name="evaluation"></a>
This step is only available for issues from the SWE-bench set. To evaluate generated pull requests:
```bash
cd evaluation/
./run_eval.sh <predictions_path>
```
Replace `<predictions_path>` with the path to the model's predictions, which should be generated from the *Inference* step. The `<predictions_path>` arguments should look like `../trajectories/<username>/<model>-<dataset>-<hyperparams>/all_preds.jsonl`
* See the [`evaluation/`](evaluation/) folder for details about how evaluation works.

## 🦺 Modifying SWE-agent <a name="modifying"></a>
If you'd like to modify the example demonstration that we feed the model at the start of each run, first generate a trajectory manually by running the agent with ```--model_name human``` 
and then convert that trajectory into a demonstration by following the guide [here](https://github.com/princeton-nlp/SWE-agent/tree/main/make_demos). 

To edit text in ```human``` mode:
1. Run the command ```edit edit_start_line:edit_end_line```
2. Write the text you want to insert. Feel free to write the text across multiple lines. 
3. Press ```return``` then write ```end_of_edit``` and then press ```return``` again to submit the edit.

## 💫 Contributions <a name="contributions"></a>
- If you'd like to ask questions, learn about upcoming features, and participate in future development, join our [Discord community](https://discord.gg/AVEFbBn2rH)!
- If you'd like to contribute to the codebase, we welcome [issues](https://github.com/princeton-nlp/SWE-agent/issues) and [pull requests](https://github.com/princeton-nlp/SWE-agent/pulls)!
- If you'd like to see a post or tutorial about some topic, please let us know via an [issue](https://github.com/princeton-nlp/SWE-agent/issues).

Contact person: [John Yang](https://john-b-yang.github.io/) and [Carlos E. Jimenez](http://www.carlosejimenez.com/) (Email: {jy1682, carlosej}@princeton.edu).

## 🪪 License <a name="license"></a>
MIT. Check `LICENSE`.

<div align="center">

[![Pytest](https://github.com/princeton-nlp/SWE-agent/actions/workflows/pytest.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/pytest.yaml)
[![Test build containers](https://github.com/princeton-nlp/SWE-agent/actions/workflows/test_build_containers.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/test_build_containers.yaml)
[![codecov](https://codecov.io/gh/princeton-nlp/SWE-agent/graph/badge.svg?token=18XAVDK365)](https://codecov.io/gh/princeton-nlp/SWE-agent)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/princeton-nlp/SWE-agent/main.svg)](https://results.pre-commit.ci/latest/github/princeton-nlp/SWE-agent/main)
[![Markdown links](https://github.com/princeton-nlp/SWE-agent/actions/workflows/check-links.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/check-links.yaml)

</div>
