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
你可以在我們的ICLR 2024的論文<a href="http://swe-bench.github.io/paper.pdf">《SWE-bench: Can Language Models Resolve Real-World GitHub Issues?》</a>中找到我們的代碼和數據
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

請訪問我們的[網站](http://swe-bench.github.io)查看公共排行榜，並查看[更改日誌](https://github.com/princeton-nlp/SWE-bench/blob/master/CHANGELOG.md)以獲取有關 SWE-bench 基準最新更新的信息。

## 👋 縱覽
SWE-bench 是一個用於評估大型語言模型的基準，這些模型是從 GitHub 收集的真實軟體問題。
給定一個 *代碼庫* 和一個 *問題*，語言模型的任務是生成一個 *修補程式* 來解決所描述的問題。

<img src="assets/teaser.png">

## 🚀 設置
要從源代碼構建 SWE-bench，請按照以下步驟操作:
1. 克隆此倉庫到本地
2. `cd` 進入倉庫
3. 運行 `conda env create -f environment.yml` 創建名為 `swe-bench` 的 conda 環境
4. 使用 `conda activate swe-bench` 激活環境

## 💽 使用
你可以直接下載 SWE-bench 數據集 ([開發](https://drive.google.com/uc?export=download&id=1SbOxHiR0eXlq2azPSSOIDZz-Hva0ETpX), [測試](https://drive.google.com/uc?export=download&id=164g55i3_B78F6EphCZGtgSrd2GneFyRM) 集) 或從 [HuggingFace](https://huggingface.co/datasets/princeton-nlp/SWE-bench) 下載。
要使用 SWE-Bench，你可以:
* 在我們預處理的數據集上訓練自己的模型
* 在現有模型上運行 [推理](https://github.com/princeton-nlp/SWE-bench/blob/master/inference/)（不管是本地的模型，比如LLaMA，還是通過API訪問的模型，比如GPT-4）。推理步驟是你獲取一個倉庫和一個問題，讓模型嘗試去修復它。
* 對模型進行 [評估](https://github.com/princeton-nlp/SWE-bench/blob/master/inference/)。這是你拿到一個 SWE-Bench 任務和一個模型提出的解決方案，然後評估其正確性。
* 在你自己的倉庫上運行 SWE-bench 的 [數據收集過程](https://github.com/princeton-nlp/SWE-bench/blob/master/collect/)，以創建新的 SWE-Bench 任務。

## ⬇️ 下載
| 數據集                                                                                                           | 模型                                                                                 |
|---------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [🤗 SWE-bench](https://huggingface.co/datasets/princeton-nlp/SWE-bench)                                       | [🦙 SWE-Llama 13b](https://huggingface.co/princeton-nlp/SWE-Llama-13b)             |
| [🤗 "Oracle" Retrieval](https://huggingface.co/datasets/princeton-nlp/SWE-bench_oracle)                       | [🦙 SWE-Llama 13b (PEFT)](https://huggingface.co/princeton-nlp/SWE-Llama-13b-peft) |
| [🤗 BM25 Retrieval 13K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_13K)                     | [🦙 SWE-Llama 7b](https://huggingface.co/princeton-nlp/SWE-Llama-7b)               |
| [🤗 BM25 Retrieval 27K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_27K)                     | [🦙 SWE-Llama 7b (PEFT)](https://huggingface.co/princeton-nlp/SWE-Llama-7b-peft)   |
| [🤗 BM25 Retrieval 40K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_40K)                     |                                                                                    |
| [🤗 BM25 Retrieval 50K (Llama tokens)](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_50k_llama) |                                                                                    |

## 🍎 教程
我們還撰寫了以下有關如何使用SWE-bench不同部分的博客文章。
如果您想看到有關特定主題的文章，請通過問題告訴我們。
* [Nov 1. 2023] Collecting Evaluation Tasks for SWE-Bench ([🔗](https://github.com/princeton-nlp/SWE-bench/tree/main/tutorials/collection.md))
* [Nov 6. 2023] Evaluating on SWE-bench ([🔗](https://github.com/princeton-nlp/SWE-bench/tree/main/tutorials/evaluation.md))

## 💫 貢獻
我們很樂意聽取來自更廣泛的 NLP、機器學習和軟體工程研究社區的意見，並歡迎任何貢獻、拉取請求或問題！
為此請提交新的拉取請求或問題，並根據相應的模板填寫。我們將盡快跟進！

聯繫人: [Carlos E. Jimenez](http://www.carlosejimenez.com/) 和 [John Yang](https://john-b-yang.github.io/) (Email: {carlosej, jy1682}@princeton.edu).

## ✍️ 引用
如果你覺得我們的工作有幫助，請使用以下引用。
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

## 🪪 授權
MIT. 參考 `LICENSE.md`.
