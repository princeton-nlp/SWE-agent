# Frequently Asked Questions

> How can I change the demonstrations given to SWE-agent?

At the start of each run, we feed the agent a demonstration trajectory, showing it how to solve an example issue. 
This substantially improves the agent's abilities to solve novel issues. 
If you'd like to modify or totally change this demonstration, to better fit your use case, see [this](config/demonstrations.md).

> Does SWE-agent run on windows?

You can run it in a [docker container](installation/docker.md), though this is not our first
choice for running SWE-agent. SWE-agent runs best on Mac and Linux, as these are the environments we use for SWE-agent development. 
We're open to merge simple fixes to make the [development setup](installation/source.md) work on Windows. 

> Which LMs do you support?

Currently our model support is limited, mostly focused on GPT-4 and Claude 3. SWE-agent will not perform well with small or local models.
[More information on models](usage/usage_faq.md).
