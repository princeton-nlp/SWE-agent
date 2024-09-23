# Agent Computer Interface (ACI)

We accomplish our results by designing simple LM-centric commands and feedback formats to make it easier for the LM to browse the repository, view, edit and execute code files. We call this an **Agent-Computer Interface** (ACI) and build the SWE-agent repository to make it easy to iterate on ACI design for repository-level coding agents.

Just like how typical language models requires good prompt engineering, **good ACI design leads to much better results when using agents**. As we show in our [paper](https://arxiv.org/abs/2405.15793), a baseline agent without a well-tuned ACI does much worse than SWE-agent.

SWE-agent contains features that we discovered to be immensely helpful during the agent-computer interface design process:

1. We add a **linter** that runs when an edit command is issued, and do not let the edit command go through if the code isn't syntactically correct.
2. We supply the agent with a **special-built file viewer**, instead of having it just `cat` files. We found that this file viewer works best when displaying just 100 lines in each turn. The **file editor** that we built has commands for scrolling up and down and for performing a search within the file.
3. We supply the agent with a special-built full-directory string **searching command**. We found that it was important for this tool to succinctly list the matches- we simply list each file that had at least one match. Showing the model more context about each match proved to be too confusing for the model.
4. When commands have an empty output we return a message saying "Your command ran successfully and did not produce any output."

Read our paper for more details [here](https://arxiv.org/abs/2405.15793).
A recent extension of our ACI are [Interactive Agent Tools](iat.md).