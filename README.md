<p align="center">
  <a href="https://www.swe-agent.com/">
    <img src="assets/swe-agent-banner.png" alt="swe-agent.com" style="height: 13em" />
  </a>
</p>

<p align="center">
  <a href="https://princeton-nlp.github.io/SWE-agent/"><strong>Documentation</strong></a>&nbsp; | &nbsp;
  <a href="https://discord.gg/AVEFbBn2rH"><strong>Discord</strong></a>&nbsp; | &nbsp;
  <a href="https://arxiv.org/abs/2405.15793"><strong>Preprint</strong></a>
</p>

**SWE-agent turns LMs (e.g. GPT-4o, Claude 3.5 Sonnet) into software engineering agents that can resolve issues in real GitHub repositories and more.**

We accomplish our results by designing simple LM-centric commands and feedback formats to make it easier for the LM to browse the repository, view, edit and execute code files. We call this an **Agent-Computer Interface (ACI)**.
Read more about it in our [paper](https://arxiv.org/abs/2405.15793)!

SWE-agent is built and maintained by researchers from Princeton 🐯 and Stanford 🌲 University.

TODO: Create a better demo video
![swe-agent-gui-demo](https://github.com/princeton-nlp/SWE-agent/assets/13602468/fa201621-ec31-4644-b658-c1d0feb92253)

Interested in SWE-agent's CTF capabilities? Check out [SWE-agent EnIGMA](https://github.com/princeton-nlp/SWE-agent/tree/enigma)!

## 🚀 Get started!

👉 Try SWE-agent in your browser: [![Open in GitHub Codespaces](https://img.shields.io/badge/Open_in_GitHub_Codespaces-gray?logo=github)](https://codespaces.new/princeton-nlp/SWE-agent) ([more information](https://princeton-nlp.github.io/SWE-agent/installation/codespaces/))

Read our [documentation](https://princeton-nlp.github.io/SWE-agent/) to learn more:

* [Installation](https://princeton-nlp.github.io/SWE-agent/installation/)
* [Command line usage](https://princeton-nlp.github.io/SWE-agent/usage/cl_tutorial/)
* [Using the web UI](https://princeton-nlp.github.io/SWE-agent/usage/web_ui/)
* [Benchmarking on SWE-bench](https://princeton-nlp.github.io/SWE-agent/usage/benchmarking/)
* [Frequently Asked Questions](https://princeton-nlp.github.io/SWE-agent/faq/)

For a more thorough walkthrough, check out [Kilian's ▶️ 1 hr Tutorial Video](https://youtu.be/d9gcXpiiDao) that breaks down the in's and out's of using SWE-agent.

## 🏛️ About 
SWE-agent is an academic project started at Princeton University by John Yang*, Carlos E. Jimenez*, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, and Ofir Press.
Contact person: [John Yang](https://john-b-yang.github.io/), [Carlos E. Jimenez](http://www.carlosejimenez.com/), and [Kilian Lieret](https://www.lieret.net/) (Email: johnby@stanford.edu, carlosej@princeton.edu, kl5675@princeton.edu).

## 💫 Contributions <a name="contributions"></a>
- If you'd like to ask questions, learn about upcoming features, and participate in future development, join our [Discord community](https://discord.gg/AVEFbBn2rH)!
- If you'd like to contribute to the codebase, we welcome [issues](https://github.com/princeton-nlp/SWE-agent/issues) and [pull requests](https://github.com/princeton-nlp/SWE-agent/pulls)!

## 📝 Citation <a name="citation"></a>
If you found this work helpful, please consider citing it using the following:
```bibtex
@misc{yang2024sweagent,
      title={SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering},
      author={John Yang and Carlos E. Jimenez and Alexander Wettig and Kilian Lieret and Shunyu Yao and Karthik Narasimhan and Ofir Press},
      year={2024},
      eprint={2405.15793},
      archivePrefix={arXiv},
      primaryClass={cs.SE}
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
