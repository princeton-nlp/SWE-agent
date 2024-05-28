<p align="center">
  <a href="https://www.swe-agent.com/">
    <img src="assets/swe-agent-banner.png" alt="swe-agent.com" />
  </a>
</p>


<p align="center">
  <a href="https://swe-agent.com"><strong>Website & Demo</strong></a>&nbsp; | &nbsp;
  <a href="https://princeton-nlp.github.io/SWE-agent/"><strong>Documentation</strong></a>&nbsp; | &nbsp;
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

## 🚀 Get started!

All information is provided in our [documentation][docs]:

* [Installation](https://princeton-nlp.github.io/SWE-agent/installation/)
* [Command line usage](https://princeton-nlp.github.io/SWE-agent/usage/cl_tutorial/)
* [Using the web UI](https://princeton-nlp.github.io/SWE-agent/usage/web_ui/)
* [Benchmarking on SWE-bench](https://princeton-nlp.github.io/SWE-agent/usage/benchmarking/)

and many more topics.

<div align="center">
<a href="https://princeton-nlp.github.io/SWE-agent/"><img src="assets/doc-scrot.png" style="width: 500px"/></a>
</div>

[docs]: https://princeton-nlp.github.io/SWE-agent/

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
[![Release to dockerhub](https://github.com/princeton-nlp/SWE-agent/actions/workflows/release-dockerhub.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/release-dockerhub.yaml)
[![build-docs](https://github.com/princeton-nlp/SWE-agent/actions/workflows/build-docs.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/build-docs.yaml)
[![codecov](https://codecov.io/gh/princeton-nlp/SWE-agent/graph/badge.svg?token=18XAVDK365)](https://codecov.io/gh/princeton-nlp/SWE-agent)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/princeton-nlp/SWE-agent/main.svg)](https://results.pre-commit.ci/latest/github/princeton-nlp/SWE-agent/main)
[![Markdown links](https://github.com/princeton-nlp/SWE-agent/actions/workflows/check-links.yaml/badge.svg)](https://github.com/princeton-nlp/SWE-agent/actions/workflows/check-links.yaml)

</div>
