#!/usr/bin/env python3

"""Provided a source (raw) directory and the final (eval) directory, create a training split by removing all instances that are in the final directory from the source directory.
"""

import os
import logging
from argparse import ArgumentParser
from pathlib import Path

import tiktoken
from datasets import disable_caching, load_from_disk, load_dataset
from tqdm.auto import tqdm
from transformers import LlamaTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.warning("Disabling caching")
disable_caching()


def cl100k(text, tokenizer):
    return tokenizer.encode(text, disallowed_special=())


def llama(text, tokenizer):
    return tokenizer(text, add_special_tokens=False, return_attention_mask=False)[
        "input_ids"
    ]


TOKENIZER_FUNCS = {
    "cl100k": (tiktoken.get_encoding("cl100k_base"), cl100k),
    "llama": (LlamaTokenizer.from_pretrained("togethercomputer/LLaMA-2-7B-32K"), llama),
}


def extract_fields(instance, tokenizer_name, tokenizer, tokenizer_func, eos_token):
    instance_id = instance["instance_id"]
    if instance["text"] is None or instance["patch"] is None:
        print(f"No text for {instance_id}")
        return {"input_ids": [], "labels": [], "text": "", "patch": ""}
    text_inputs = instance["text"].strip() + "\n"
    if text_inputs is None or instance["patch"] is None:
        print(f"No inputs for {instance_id}")
        return None
    patch = instance["patch"].strip()
    if len(eos_token) > 0:
        patch += f"\n{eos_token}"
    input_ids = tokenizer_func(text_inputs, tokenizer)
    if tokenizer_name in {"llama"}:
        label_ids = tokenizer_func(
            "\n" + patch, tokenizer
        )  # add newline to tokenize patch
        idx = label_ids.index(13)
        assert (
            idx <= 2
        ), "Expected newline token id (13) to be one of the first three tokens"
        label_ids = label_ids[idx + 1 :]  # remove newline tokens
    else:
        label_ids = tokenizer_func(patch, tokenizer)
    inputs = input_ids + label_ids[:-1]
    cond_len = len(input_ids) - 1
    labels = [-100] * cond_len + label_ids
    assert len(inputs) == len(labels)
    return {**instance, "input_ids": inputs, "labels": labels, "text": text_inputs, "patch": patch}


def extract_test_fields(instance, tokenizer_name, tokenizer, tokenizer_func, eos_token):
    instance_id = instance["instance_id"]
    if instance["text"] is None or instance["patch"] is None:
        print(f"No text for {instance_id}")
        return None
    text_inputs = instance["text"].strip() + "\n"
    if text_inputs is None or instance["patch"] is None:
        print(f"No inputs for {instance_id}")
        return None
    patch = instance["patch"].strip()
    if len(eos_token) > 0:
        patch += f"\n{eos_token}"
    input_ids = tokenizer_func(text_inputs, tokenizer)
    label_ids = tokenizer_func(patch, tokenizer)
    inputs = input_ids
    labels = label_ids
    return {**instance, "input_ids": inputs, "labels": labels, "text": text_inputs, "patch": patch}


def add_columns_from_dict(dataset, dict_columns):
    """dict_columns is a list of dicts with keys that are columns in dataset"""
    for column in dict_columns[0].keys():
        values = [d[column] for d in dict_columns]
        if column in dataset.column_names:
            dataset = dataset.remove_columns(column)
        dataset = dataset.add_column(column, values)
    return dataset


def main(
    dataset_name_or_path,
    output_dir,
    tokenizer_name,
    num_proc,
    push_to_hub_user,
):
    if push_to_hub_user is not None:
        hub_token = os.environ.get("HUGGING_FACE_HUB_TOKEN", None)
        if hub_token is None:
            raise ValueError("Must provide HUGGING_FACE_HUB_TOKEN to push to the Hub")
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True)

    if tokenizer_name is not None:
        tokenizer, tokenizer_func = TOKENIZER_FUNCS[tokenizer_name]
        eos_token = getattr(tokenizer, "eos_token", "")
        if num_proc > 0 and tokenizer_name == 'cl100k':
            logger.warning('cl100k tokenizer does not support multiprocessing. Ignoring num_proc')
            num_proc = 0

    if Path(dataset_name_or_path).exists():
        dataset = load_from_disk(dataset_name_or_path)
    else:
        dataset = load_dataset(dataset_name_or_path)
    dataset = dataset.filter(lambda x: len(x["text"]) <= 5_000_000)  # filter out superlong instances
    for split in dataset.keys():
        if split == "test":
            continue
        if num_proc > 0:
            dataset[split] = dataset[split].map(
                lambda instance: extract_fields(
                    instance,
                    tokenizer_name,
                    tokenizer,
                    tokenizer_func,
                    eos_token,
                ),
                num_proc=num_proc,
                batched=False,
                desc=f"Tokenizing {split}",
            )
        elif len(dataset[split]) > 0:
            new_values = list(
                map(
                    lambda x: extract_fields(
                        x, tokenizer_name, tokenizer, tokenizer_func, eos_token
                    ),
                    tqdm(
                        dataset[split],
                        total=len(dataset[split]),
                        desc=f"Tokenizing {split}",
                    ),
                )
            )
            dataset[split] = add_columns_from_dict(dataset[split], new_values)
    for split in ["test"]:
        if split not in dataset:
            logger.warning(f"Split {split} not in dataset. Skipping")
            continue
        if num_proc > 0:
            dataset[split] = dataset[split].map(
                lambda instance: extract_test_fields(
                    instance,
                    tokenizer_name,
                    tokenizer,
                    tokenizer_func,
                    eos_token,
                ),
                num_proc=num_proc,
                batched=False,
                desc=f"Tokenizing {split}",
            )
        elif len(dataset[split]) > 0:
            new_values = list(
                map(
                    lambda x: extract_test_fields(
                        x, tokenizer_name, tokenizer, tokenizer_func, eos_token
                    ),
                    tqdm(
                        dataset[split],
                        total=len(dataset[split]),
                        desc=f"Tokenizing {split}",
                    ),
                )
            )
            dataset[split] = add_columns_from_dict(dataset[split], new_values)
    output_file = Path(dataset_name_or_path).name + f"__tok-{tokenizer_name}"
    if push_to_hub_user is not None:
        output_file = f"{push_to_hub_user}/{output_file}"
        dataset.push_to_hub(output_file, use_auth_token=hub_token)
    else:
        output_file = Path(output_dir) / output_file
        dataset.save_to_disk(output_file)
    logger.warning(f"Saved to {output_file}")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset_name_or_path", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument(
        "--tokenizer_name", type=str, required=True, choices=TOKENIZER_FUNCS.keys()
    )
    parser.add_argument("--num_proc", type=int, default=0)
    parser.add_argument(
        "--push_to_hub_user",
        type=str,
        default=None,
        help="Push the dataset to the Hub user under this name.",
    )
    main(**vars(parser.parse_args()))
