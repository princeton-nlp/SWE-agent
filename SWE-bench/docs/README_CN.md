<p align="center">
  <a href="https://github.com/princeton-nlp/Llamao">
    <img src="assets/swellama_banner.png" width="50%" alt="Kawi the SWE-Llama" />
  </a>
</p>

<div align="center">

 | [日本語](docs/README_JP.md) | [English](https://github.com/princeton-nlp/SWE-bench) | [中文简体](docs/README_CN.md) | [中文繁體](docs/README_TW.md) |

</div>


---
<p align="center">
您可以在我们的ICLR 2024的论文<a href="http://swe-bench.github.io/paper.pdf">《SWE-bench: Can Language Models Resolve Real-World GitHub Issues?》</a>中找到我们的代码和数据
    </br>
    </br>
    <a href="https://www.python.org/">
        <img alt="Build" src="https://img.shields.io/badge/Python-3.8+-1f425f.svg?color=purple">
    </a>
    <a href="https://copyright.princeton.edu/policy">
        <img alt="License" src="https://img.shields.io/badge/License-MIT-blue">
    </a>
    <a href="https://badge.fury.io/py/swebench">
        <img src="https://badge.fury.io/py/swebench.svg">
    </a>
</p>

请访问我们的[网站](http://swe-bench.github.io)查看公共排行榜，并查看[更改日志](https://github.com/princeton-nlp/SWE-bench/blob/master/CHANGELOG.md)以获取有关 SWE-bench 基准最新更新的信息。

## 👋 总览
SWE-bench 是一个用于评估大型语言模型的基准，这些模型是从 GitHub 收集的真实软件问题。
给定一个 *代码库* 和一个 *问题*，语言模型的任务是生成一个 *补丁* 来解决所描述的问题。

<img src="assets/teaser.png">

## 🚀 设置
要从源代码构建 SWE-bench，请按照以下步骤操作:
1. 克隆此仓库到本地
2. `cd` 进入仓库
3. 运行 `conda env create -f environment.yml` 创建名为 `swe-bench` 的 conda 环境
4. 使用 `conda activate swe-bench` 激活环境

## 💽 使用
你可以直接下载 SWE-bench 数据集 ([开发](https://drive.google.com/uc?export=download&id=1SbOxHiR0eXlq2azPSSOIDZz-Hva0ETpX), [测试](https://drive.google.com/uc?export=download&id=164g55i3_B78F6EphCZGtgSrd2GneFyRM) 集) 或从 [HuggingFace](https://huggingface.co/datasets/princeton-nlp/SWE-bench) 下载。
要使用 SWE-Bench，你可以:
* 在我们预处理的数据集上训练自己的模型
* 在现有模型上运行 [推理](https://github.com/princeton-nlp/SWE-bench/blob/master/inference/) （不管是本地的模型，比如LLaMA，还是通过API访问的模型，比如GPT-4）。推理步骤是你获取一个仓库和一个问题，让模型尝试去修复它。
* 对模型进行 [评估](https://github.com/princeton-nlp/SWE-bench/blob/master/harness/)。这是你拿到一个 SWE-Bench 任务和一个模型提出的解决方案，然后评估其正确性。
* 在你自己的仓库上运行 SWE-bench 的 [数据收集过程](https://github.com/princeton-nlp/SWE-bench/blob/master/collect/)，以创建新的 SWE-Bench 任务。

## ⬇️ 下载
| 数据集                                                                                                            | 模型                                                                                 |
|----------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [🤗 SWE-bench](https://huggingface.co/datasets/princeton-nlp/SWE-bench)                                        | [🦙 SWE-Llama 13b](https://huggingface.co/princeton-nlp/SWE-Llama-13b)             |
| [🤗 "Oracle" Retrieval](https://huggingface.co/datasets/princeton-nlp/SWE-bench_oracle)                        | [🦙 SWE-Llama 13b (PEFT)](https://huggingface.co/princeton-nlp/SWE-Llama-13b-peft) |
| [🤗 BM25 Retrieval 13K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_13K)                      | [🦙 SWE-Llama 7b](https://huggingface.co/princeton-nlp/SWE-Llama-7b)               |
| [🤗 BM25 Retrieval 27K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_27K)                      | [🦙 SWE-Llama 7b (PEFT)](https://huggingface.co/princeton-nlp/SWE-Llama-7b-peft)   |
| [🤗 BM25 Retrieval 40K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_40K)                      |                                                                                    |
| [🤗 BM25 Retrieval 50K (Llama tokens)](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_50k_llama) |                                                                                    |

## 🍎 教程
我们还写了关于如何使用SWE-bench不同部分的博客文章。
如果您想看到关于特定主题的文章，请通过问题告诉我们。
* [Nov 1. 2023] Collecting Evaluation Tasks for SWE-Bench ([🔗](https://github.com/princeton-nlp/SWE-bench/tree/main/tutorials/collection.md))
* [Nov 6. 2023] Evaluating on SWE-bench ([🔗](https://github.com/princeton-nlp/SWE-bench/tree/main/tutorials/evaluation.md))

## 💫 贡献
我们欢迎来自更广泛的自然语言处理、机器学习和软件工程研究社区的反馈。我们欢迎任何贡献、PR或问题!
为此，请提交新的PR或问题，并相应地填写相应的模板。我们将尽快跟进!

联系人: [Carlos E. Jimenez](http://www.carlosejimenez.com/) 和 [John Yang](https://john-b-yang.github.io/) (Email: {carlosej, jy1682}@princeton.edu).

## ✍️ 引用
如果你觉得我们的工作有帮助，请使用以下引用。
```
@inproceedings{
    jimenez2024swebench,
    title={{SWE}-bench: Can Language Models Resolve Real-world Github Issues?},
    author={Carlos E Jimenez and John Yang and Alexander Wettig and Shunyu Yao and Kexin Pei and Ofir Press and Karthik R Narasimhan},
    booktitle={The Twelfth International Conference on Learning Representations},
    year={2024},
    url={https://openreview.net/forum?id=VTF8yNQM66}
}
```

## 🪪 许可证
MIT. 参考 `LICENSE.md`.
