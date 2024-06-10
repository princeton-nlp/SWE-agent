# `make_datasets`
The `make_datasets` sub-package is used to create datasets for SWE-bench with your own prompts, contexts, and tokenizers.
The sub-package contains the following scripts:

- `create_text_dataset.py` is used to create a text dataset from SWE-bench with a given prompt and context-source.
- `tokenize_dataset.py` is used to tokenize a text dataset with a given tokenizer.
- `bm25_retrieval.py` can be used to perform BM25 retrieval on the SWE-bench dataset.

## `create_text_dataset.py`
This script is used to create a text dataset from SWE-bench with a given prompt and context-source.
Prompts are defined as functions in `create_instance.py`. `style-2` and `style-3` are appropriate for API models, while only `style-2` can be used for SWE-Llama.
`full_file_gen` is used for the full file generation ablation, and `style-2-edits-only`  is used for the `oracle-collapsed` ablation.

Here's an example of how to call the script to create a dataset with `style-3` prompts and `oracle` contexts:

```bash
export GITHUB_TOKEN=<your token>
python create_text_dataset.py --dataset_name_or_path princeton-nlp/SWE-bench --output_dir ./base_datasets --prompt_style style-3 --file_source oracle
```

You can also specify further options:

- `--splits`: To specify the dataset splits to process (default is all splits). If you want to process only the `test` split, you can use `--splits test`.
- `--validation_ratio`: To specify the ratio of the training set to use for validation (default is 0.01). For example, you can use `--validation_ratio 0.05` to use 5% of the training set for validation.
- `--max_context_len`: To specify the maximum number of tokens to use for context. For example, `--max_context_len 15000` will limit the context to 15000 tokens.
- `--tokenizer_name`: To specify the tokenizer to use. You can choose from the available tokenizers defined in `tokenize_dataset.py`. If not specified, the default tokenizer will be used.
- `--push_to_hub_user`: If you want to push the dataset to the Hugging Face Hub, you can specify your username with this option. If specified, make sure you have set your API key environment variable `HUGGING_FACE_HUB_TOKEN`. You do not need to specify `--output_dir` if you use this option.
- `--retrieval_file`: If you want to use BM25 retrieval to create the dataset, you can specify the file containing the retrieval results with this option. The retrieval results should be in the format produced by `bm25_retrieval.py`. You should specify `--file_source bm25` if you use this option.

The script will create a new dataset in the specified output directory. If you choose to push the dataset to the Hugging Face Hub, it will be available under your username.

## `tokenize_dataset.py`
This script is used to tokenize a text dataset with a given tokenizer. You can choose from the available tokenizers defined in the script. The script will create a new tokenized dataset in the specified output directory.

Here's an example of how to call the script to tokenize a dataset with the `llama` tokenizer:

```bash
python tokenize_dataset.py --dataset_name_or_path ./base_datasets/DATASET_NAME --output_dir ./tokenized_datasets --tokenizer_name llama --num_proc 20
```

- `--push_to_hub_user`: If you want to push the dataset to the Hugging Face Hub, you can specify your username with this option. If specified, make sure you have set your API key environment variable `HUGGING_FACE_HUB_TOKEN`. You do not need to specify `--output_dir` if you use this option.

__NOTE:__ The `cl100k` tokenizer does not support multiprocessing.

## `bm25_retrieval.py`
This script can be used to perform BM25 retrieval on the SWE-bench dataset. It creates a results file in the specified output directory that can be used in `create_text_dataset.py` with the `--retrieval_file` option and `--file_source bm25`.

Here's an example of how to call the script to perform BM25 retrieval on the `test` split of the SWE-bench dataset:

```bash
python bm25_retrieval.py --dataset_name_or_path princeton-nlp/SWE-bench --output_dir ./retrieval_results --splits test
```

__NOTE:__ The script requires the `pyserini` package to be installed. See the pyserini [installation instructions](https://github.com/castorini/pyserini) for more details.


## `eval_retrieval.py`
This script can be used to evaluate the BM25 retrieval results for a dataset created with `create_text_dataset.py` with the `--retrieval_file` option and `--file_source bm25`.
__NOTE__: The script assumes that the `text` field in the dataset specifies files using the "\[start of filename\]" and "\[end of filename\]" tags used by the default DOCUMENT_ENCODING_FUNCTIONS in `bm25_retrieval.py`. If you change that format, you need to modify the `instance_file_pattern` in `eval_retrieval.py` accordingly.

Here's an example of how to call the script to evaluate the BM25 retrieval results for a dataset:

```bash
python eval_retrieval.py --dataset_name_or_path princeton-nlp/SWE-bench_bm25_13K --split test
```
