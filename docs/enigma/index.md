# Learn more about the EnIGMA project.

This section of the documentation talks about the architecture and research goals of EnIGMA.

Just want to run EnIGMA? Skip ahead to our [installation notes](../installation/index.md).

EnIGMA (Enhanced Interactive Generative Model Agent) is an LM agent built on top of SWE-agent for solving Capture The Flag (CTF) cybersecurity challenges.

The challenges range in various categories: cryptography, reverse-engineering, forensics, binary exploitation, web security and miscellaneous.

On [NYU CTF benchmark](https://github.com/NYU-LLM-CTF/LLM_CTF_Database), EnIGMA solves **13.5%** of challenges, achieving the state-of-the-art performance on the full test set of 200 CTF challenges.

We accomplish our results by extending the [🤖 Agent-Computer Interfaces (ACIs)](../background/aci.md) first introduced in SWE-agent, to the cybersecurity domain. We establish the novel **:gear: Interactive Agent Tools** (IATs) concept, which enables our agent to use interactive tools such as a debugger, in a multiprocess way such that the agent still has access to the main shell. Read more about IAT [here](iat.md).

We also use a new **Summarizer** concept integrated into the agent to deal with long context. Read more about our different summarizers [here](../config/summarizers.md).

Specific [demonstrations](../config/demonstrations.md) were built per each CTF category, to enhance the model ability to solve new tasks from the same category.

EnIGMA is built and maintained by researchers from Tel-Aviv University, New York University and Princeton University.

For a quick introduction, watch the following video:

// Add video here

If you found this work helpful, please consider using the following citation:

```
add bibtex here
```