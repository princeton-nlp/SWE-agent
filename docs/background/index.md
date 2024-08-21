# Learn more about the SWE-agent project.

This section of the documentation talks about the architecture and research goals of SWE-agent.

Just want to run SWE-agent? Skip ahead to our [installation notes](../installation/index.md).

SWE-agent turns LMs (e.g. GPT-4) into software engineering agents that can fix issues in GitHub repositories.

On [SWE-bench](https://github.com/princeton-nlp/SWE-bench), SWE-agent resolves **12.29%** of issues, achieving the state-of-the-art performance on the full test set.

We accomplish our results by designing simple LM-centric commands and feedback formats to make it easier for the LM to browse the repository, view, edit and execute code files. We call this an 🤖 **Agent-Computer Interface (ACI)**.
Read more about the ACI [here](aci.md).

SWE-agent is built and maintained by researchers from Princeton University.

For a quick introduction, watch the following video:

<iframe width="560" height="315" src="https://www.youtube.com/embed/CeMtJ4XObAM?si=W2tyY9EpEe-v12EU" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

A longer lecture touching on the project's motivation, research findings, as well as providing a hands-on tutorial on how to install, use, and configure SWE-agent is provided here:

<iframe width="560" height="315" src="https://www.youtube.com/embed/d9gcXpiiDao" title="NeurIPS Hacker Cup AI: SWEAgent" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

If you found this work helpful, please consider using the following citation:

```
@misc{yang2024sweagent,
      title={SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering},
      author={John Yang and Carlos E. Jimenez and Alexander Wettig and Kilian Lieret and Shunyu Yao and Karthik Narasimhan and Ofir Press},
      year={2024},
}
```