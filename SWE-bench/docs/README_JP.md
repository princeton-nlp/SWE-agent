<documents>
<document index="1">
<source>paste.txt</source>
<document_content>
<p align="center">
  <a href="https://github.com/princeton-nlp/Llamao">
    <img src="https://raw.githubusercontent.com/Sunwood-ai-labs/SWE-bench/main/assets/swellama_banner.png" width="50%" alt="Kawi the SWE-Llama" />
  </a>
</p>

<div align="center">

 | [日本語](docs/README_JP.md) | [English](https://github.com/princeton-nlp/SWE-bench) | [中文简体](docs/README_CN.md) | [中文繁體](docs/README_TW.md) |

</div>


---
<p align="center">
ICLR 2024 の論文 <a href="http://swe-bench.github.io/paper.pdf">SWE-bench: Can Language Models Resolve Real-World GitHub Issues?</a> のコードとデータ
    </br>
    </br>
    <a href="https://www.python.org/">
        <img alt="Build" src="https://img.shields.io/badge/Python-3.8+-1f425f.svg?color=purple">
    </a>
    <a href="https://copyright.princeton.edu/policy">
        <img alt="License" src="https://img.shields.io/badge/License-MIT-blue">
    </a>
</p>

パブリックリーダーボードは[ウェブサイト](http://swe-bench.github.io)を、SWE-bench ベンチマークの最新アップデート情報は [change log](https://github.com/princeton-nlp/SWE-bench/blob/master/CHANGELOG.md) を参照してください。

## 👋 概要 
SWE-bench は、GitHub から収集された実世界のソフトウェアの課題に関する大規模言語モデルを評価するためのベンチマークです。
*コードベース*と*イシュー*が与えられ、言語モデルは記述された問題を解決する*パッチ*を生成するタスクを行います。

<img src="https://raw.githubusercontent.com/Sunwood-ai-labs/SWE-bench/main/assets/teaser.png">

## 🚀 セットアップ
SWE-bench をソースからビルドするには、以下の手順に従ってください:
1. このリポジトリをローカルにクローンする
2. リポジトリに `cd` で移動する
3. `conda env create -f environment.yml` を実行して、`swe-bench` という名前の conda 環境を作成する  
4. `conda activate swe-bench` で環境をアクティベートする

## 💽 使用法
SWE-bench データセットは直接ダウンロードするか ([dev](https://drive.google.com/uc?export=download&id=1SbOxHiR0eXlq2azPSSOIDZz-Hva0ETpX), [test](https://drive.google.com/uc?export=download&id=164g55i3_B78F6EphCZGtgSrd2GneFyRM) セット)、[HuggingFace](https://huggingface.co/datasets/princeton-nlp/SWE-bench) からダウンロードできます。

SWE-Bench を使用するには、以下のことができます:
* 前処理済みのデータセットで独自のモデルを学習する
* 既存のモデル (ディスクにあるLLaMAのようなモデルやGPT-4のようなAPIでアクセスできるモデル) で[推論](https://github.com/princeton-nlp/SWE-bench/blob/master/inference/)を実行する。推論ステップでは、レポとイシューを取得し、モデルにそれを修正するためのコードを生成させます。 
* SWE-bench に対してモデルを[評価](https://github.com/princeton-nlp/SWE-bench/blob/master/harness/)する。これは、SWE-Benchのタスクとモデルが提案したソリューションを受け取り、その正確性を評価するためのものです。
* 独自のリポジトリに対してSWE-benchの[データ収集手順](https://github.com/princeton-nlp/SWE-bench/blob/master/collect/)を実行し、新しいSWE-Benchタスクを作成する。

## ⬇️ ダウンロード
| データセット | モデル |  
| - | - |
| [🤗 SWE-bench](https://huggingface.co/datasets/princeton-nlp/SWE-bench) | [🦙 SWE-Llama 13b](https://huggingface.co/princeton-nlp/SWE-Llama-13b) |
| [🤗 "Oracle" Retrieval](https://huggingface.co/datasets/princeton-nlp/SWE-bench_oracle) | [🦙 SWE-Llama 13b (PEFT)](https://huggingface.co/princeton-nlp/SWE-Llama-13b-peft) |  
| [🤗 BM25 Retrieval 13K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_13K) | [🦙 SWE-Llama 7b](https://huggingface.co/princeton-nlp/SWE-Llama-7b) |
| [🤗 BM25 Retrieval 27K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_27K) | [🦙 SWE-Llama 7b (PEFT)](https://huggingface.co/princeton-nlp/SWE-Llama-7b-peft) |
| [🤗 BM25 Retrieval 40K](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_40K) | |
| [🤗 BM25 Retrieval 50K (Llamaトークン)](https://huggingface.co/datasets/princeton-nlp/SWE-bench_bm25_50k_llama) | |  

## 🍎 チュートリアル 
SWE-benchの様々な部分の使い方についても、以下のブログ記事を書いています。
特定のトピックについての投稿を見たい場合は、issueでお知らせください。
* [2023年11月1日] SWE-Benchの評価タスクの収集について ([🔗](https://github.com/princeton-nlp/SWE-bench/tree/main/tutorials/collection.md))
* [2023年11月6日] SWE-benchでの評価について ([🔗](https://github.com/princeton-nlp/SWE-bench/tree/main/tutorials/evaluation.md))

## 💫 貢献
NLP、機械学習、ソフトウェア工学の研究コミュニティからのフィードバックを歓迎します。貢献、プルリクエスト、issueを歓迎します!
そのためには、新しいプルリクエストまたはissueを提出し、それぞれのテンプレートに従って記入してください。すぐにフォローアップします!

連絡先: [Carlos E. Jimenez](http://www.carlosejimenez.com/) と [John Yang](https://john-b-yang.github.io/) (Email: {carlosej, jy1682}@princeton.edu)

## ✍️ 引用
私たちの研究が役立つと思われる場合は、以下の引用をご利用ください。
```
@inproceedings{jimenez2024swebench,
      title={SWE-bench: Can Language Models Resolve Real-World GitHub Issues?}, 
      author={Carlos E. Jimenez and John Yang and Alexander Wettig and Shunyu Yao and Kexin Pei and Ofir Press and Karthik Narasimhan},
      booktitle={The Twelfth International Conference on Learning Representations},
      year={2024},
      url={https://openreview.net/forum?id=VTF8yNQM66}
}
```

## 🪪 ライセンス
MIT。`LICENSE.md`を確認してください。
