<p align="center">
  <a href="https://www.swe-agent.com/">
    <img src="assets/swe-agent-banner.png" alt="swe-agent.com" style="height: 12em" />
  </a>
</p>

<p align="center">
  <a href="https://princeton-nlp.github.io/SWE-agent/"><strong>Documentation</strong></a>&nbsp; | &nbsp;
  <a href="https://discord.gg/AVEFbBn2rH"><strong>Discord</strong></a>&nbsp; | &nbsp;
  <a href="https://arxiv.org/abs/2405.15793"><strong>Paper</strong></a>
</p>


SWE-agent is an open-source platform for deploying language model (LM) agents in isolated computer environments.
It manages an LM of your choice (e.g. GPT-4o, Claude Sonnet 3.5, or a local LM) to autonomously perform tasks within these environments using customizable [agent-computer interfaces](https://arxiv.org/abs/2405.15793) (ACIs).

You can use SWE-agent to:
* [automatically resolve issues in your GitHub repository](background.md#swe-agent)
* navigate the web
* solve your own custom tasks!

SWE-agent is built and maintained by researchers from Princeton University and Stanford University.

## Getting started!

### Installation
SWE-agent now depends on our remote execution platform [SWE-ReX](https://github.com/swe-agent/SWE-ReX) for running agent commands in the container.
To install SWE-ReX, you'll currently need to install it from source using pip:

```bash
git clone https://github.com/swe-agent/SWE-ReX.git swe-rex
cd swe-rex
pip install -e .
```

Once SWE-ReX is installed, you can install SWE-agent using pip:

```bash
pip install swe-agent
```

Make sure to set your API keys with
```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

### Run on a GitHub issue
```bash
sweagent run --config config/default_from_url.yaml \
    --agent.model.name "gpt-4o" \
    --env.repo.github_url https://github.com/scikit-learn/scikit-learn \
    --problem_statement.github_url https://github.com/scikit-learn/scikit-learn/issues/30353
```

### Run with a Human Agent (useful for debugging)
```bash
sweagent run --config config/default.yaml \
    --agent.model.name "human" \
    --env.repo.github_url https://github.com/scikit-learn/scikit-learn \
    --problem_statement.github_url https://github.com/scikit-learn/scikit-learn/issues/30353
```

### Run on SWE-bench
```bash
sweagent run-batch \
    --instances.type swe_bench \
    --instances.subset verified \
    --instances.split test \
    --num_workers 10 \
    --config config/default.yaml \
    --agent.model.name gpt-4o
```

## About
SWE-agent is an academic project started at Princeton University by John Yang*, Carlos E. Jimenez*, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, and Ofir Press.
Contact person: [John Yang](https://john-b-yang.github.io/), [Carlos E. Jimenez](http://www.carlosejimenez.com/), and [Kilian Lieret](https://www.lieret.net/) (Email: johnby@stanford.edu, carlosej@princeton.edu, kl5675@princeton.edu).

## Contributions <a name="contributions"></a>
- If you'd like to ask questions, learn about upcoming features, and participate in future development, join our [Discord community](https://discord.gg/AVEFbBn2rH)!
- If you'd like to contribute to the codebase, we welcome [issues](https://github.com/princeton-nlp/SWE-agent/issues) and [pull requests](https://github.com/princeton-nlp/SWE-agent/pulls)!

## Citation <a name="citation"></a>
If you found this work helpful, please consider citing it using the following:
```bibtex
@inproceedings{yang2024sweagent,
  title={{SWE}-agent: Agent-Computer Interfaces Enable Automated Software Engineering},
  author={John Yang and Carlos E Jimenez and Alexander Wettig and Kilian Lieret and Shunyu Yao and Karthik R Narasimhan and Ofir Press},
  booktitle={The Thirty-eighth Annual Conference on Neural Information Processing Systems},
  year={2024},
  url={https://arxiv.org/abs/2405.15793}
}
```

## 🪪 License <a name="license"></a>
MIT. Check `LICENSE`.

<div align="center">

[![Pytest](https://github.com/princeton-nlp/SWE-agent/actions/workflows/pytest.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/pytest.yaml)
[![Test build containers](https://github.com/princeton-nlp/SWE-agent/actions/workflows/test_build_containers.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/test_build_containers.yaml)
[![Release to dockerhub (nightly)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/release-dockerhub-nightly.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/release-dockerhub-nightly.yaml)
[![Release to dockerhub (release)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/release-dockerhub-release.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/release-dockerhub-release.yaml)
[![build-docs](https://github.com/princeton-nlp/SWE-agent/actions/workflows/build-docs.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/build-docs.yaml)
[![codecov](https://codecov.io/gh/princeton-nlp/SWE-agent/graph/badge.svg?token=18XAVDK365)](https://codecov.io/gh/princeton-nlp/SWE-agent)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/princeton-nlp/SWE-agent/main.svg)](https://results.pre-commit.ci/latest/github/princeton-nlp/SWE-agent/main)
[![Markdown links](https://github.com/princeton-nlp/SWE-agent/actions/workflows/check-links.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/check-links.yaml)

</div>
