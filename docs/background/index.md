# Learn more about the project.

This section of the documentation talks about the architecture and research goals of [SWE-agent](#swe-agent) and [EnIGMA](#enigma).

Just want to run SWE-agent or EnIGMA? Skip ahead to our [installation notes](../installation/index.md).

## SWE-agent <a name="swe-agent"></a>

SWE-agent turns LMs (e.g. GPT-4) into software engineering agents that can fix issues in GitHub repositories.

On [SWE-bench](https://github.com/princeton-nlp/SWE-bench), SWE-agent resolves **12.29%** of issues, achieving the state-of-the-art performance on the full test set.

We accomplish our results by designing simple LM-centric commands and feedback formats to make it easier for the LM to browse the repository, view, edit and execute code files. We call this an 🤖 **Agent-Computer Interface (ACI)**.
Read more about the ACI [here](aci.md).

SWE-agent is built and maintained by researchers from Princeton University.

For a quick introduction, watch the following video:

<iframe width="560" height="315" src="https://www.youtube.com/embed/CeMtJ4XObAM?si=W2tyY9EpEe-v12EU" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

A longer lecture touching on the project's motivation, research findings, as well as providing a hands-on tutorial on how to install, use, and configure SWE-agent is provided here:

<iframe width="560" height="315" src="https://www.youtube.com/embed/d9gcXpiiDao" title="NeurIPS Hacker Cup AI: SWEAgent" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

For in-depth information, read our [paper](https://arxiv.org/abs/2405.15793). If you found this work helpful, please consider using the following citation:

```bibtex
@misc{yang2024sweagent,
      title={SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering},
      author={John Yang and Carlos E. Jimenez and Alexander Wettig and Kilian Lieret and Shunyu Yao and Karthik Narasimhan and Ofir Press},
      year={2024},
}
```

## SWE-agent <span class="enigma">EnIGMA</span> <a name="enigma"></a>

SWE-agent <span class="enigma">EnIGMA</span> adds advanced **offensive cybersecurity capabilities**.

On the [NYU CTF benchmark](https://github.com/NYU-LLM-CTF/LLM_CTF_Database), EnIGMA solves **13.5%** of the capture the flag (CTF) challenges, achieving the state-of-the-art performance on the full test set of 200 challenges, **surpassing previous agents by more than 3x** ([leaderboard](https://enigma-agent.github.io/#results)).

We accomplish our results by extending the [🤖 ACIs](../background/aci.md) concept first introduced in SWE-agent, to the cybersecurity domain. We establish the novel [**:gear: Interactive Agent Tools** (IATs)](iat.md) concept, which enables our agent to use interactive tools such as a debugger, in a multitasking way such that the agent still has access to the main shell while using the debugger.

We also use a new **Summarizer** concept integrated into the agent to deal with long context. Read more about our different summarizers [here](../config/summarizers.md).

Specific [demonstrations](../config/demonstrations.md) were built per each CTF category (cryptography, reverse-engineering, forensics, ...), to enhance the model ability to solve new tasks from the same category.

EnIGMA is built and maintained by researchers from Tel-Aviv University, New York University and Princeton University.

For a quick introduction, watch the following video:

<iframe width="560" height="315" src="https://www.youtube.com/embed/IJxqOsNFiCc?si=xtIxyCcriM9FJexK" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

For all the details, read our [paper](https://arxiv.org/abs/2409.16165). If you found this work helpful, please consider using the following citation:

```bibtex
@misc{abramovich2024enigmaenhancedinteractivegenerative,
      title={EnIGMA: Enhanced Interactive Generative Model Agent for CTF Challenges},
      author={Talor Abramovich and Meet Udeshi and Minghao Shao and Kilian Lieret and Haoran Xi and Kimberly Milner and Sofija Jancheska and John Yang and Carlos E. Jimenez and Farshad Khorrami and Prashanth Krishnamurthy and Brendan Dolan-Gavitt and Muhammad Shafique and Karthik Narasimhan and Ramesh Karri and Ofir Press},
      year={2024},
      eprint={2409.16165},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2409.16165},
}
```
