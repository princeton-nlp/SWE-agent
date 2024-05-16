# SWE-agent

![test](assets/readme_assets/swe-agent-banner.png)

SWE-agent turns LMs (e.g. GPT-4) into software engineering agents that can fix bugs and issues in real GitHub repositories.

On [SWE-bench](https://github.com/princeton-nlp/SWE-bench), SWE-agent resolves **12.29%** of issues, achieving the state-of-the-art performance on the full test set.

We accomplish our results by designing simple LM-centric commands and feedback formats to make it easier for the LM to browse the repository, view, edit and execute code files. We call this an 🤖 **Agent-Computer Interface (ACI)**.
Read more about it in our [paper](https://swe-agent.com/paper.pdf)!

SWE-agent is built and maintained by researchers from Princeton University. 

<p align="center">
  <img src="assets/readme_assets/results+preview.png" style="width: 80%; height: auto;">
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