#!/usr/bin/env python3

"""This python script is designed to run inference on a dataset using either the OpenAI or Anthropic API, depending on the model specified. 
It sorts instances by length and continually writes the outputs to a specified file, so that the script can be stopped and restarted without losing progress.
"""

import json
import os
import time
import dotenv
import traceback
from pathlib import Path
from tqdm.auto import tqdm
import numpy as np
import openai
import tiktoken
from anthropic import HUMAN_PROMPT, AI_PROMPT, Anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from datasets import load_dataset, load_from_disk
from make_datasets.utils import extract_diff
from argparse import ArgumentParser
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
dotenv.load_dotenv()

MODEL_LIMITS = {
    "claude-instant-1": 100_000,
    "claude-2": 100_000,
    "claude-3-opus-20240229": 200_000,
    "claude-3-sonnet-20240229": 200_000,
    "claude-3-haiku-20240307": 200_000,
    "gpt-3.5-turbo-16k-0613": 16_385,
    "gpt-3.5-turbo-0613": 4_097,
    "gpt-3.5-turbo-1106": 16_385,
    "gpt-4-32k-0613": 32_768,
    "gpt-4-0613": 8_192,
    "gpt-4-1106-preview": 128_000,
    "gpt-4-0125-preview": 128_000,
}

# The cost per token for each model input.
MODEL_COST_PER_INPUT = {
    "claude-instant-1": 0.00000163,
    "claude-2": 0.00001102,
    "claude-3-opus-20240229": 0.000015,
    "claude-3-sonnet-20240229": 0.000003,
    "claude-3-haiku-20240307": 0.00000025,
    "gpt-3.5-turbo-16k-0613": 0.0000015,
    "gpt-3.5-turbo-0613": 0.0000015,
    "gpt-3.5-turbo-1106": 0.000001,
    "gpt-35-turbo-0613": 0.0000015,
    "gpt-35-turbo": 0.0000015,  # probably still 0613
    "gpt-4-0613": 0.00003,
    "gpt-4-32k-0613": 0.00006,
    "gpt-4-32k": 0.00006,
    "gpt-4-1106-preview": 0.00001,
    "gpt-4-0125-preview": 0.00001,
}

# The cost per token for each model output.
MODEL_COST_PER_OUTPUT = {
    "claude-instant-1": 0.00000551,
    "claude-2": 0.00003268,
    "claude-3-opus-20240229": 0.000075,
    "claude-3-sonnet-20240229": 0.000015,
    "claude-3-haiku-20240307": 0.00000125,
    "gpt-3.5-turbo-16k-0613": 0.000002,
    "gpt-3.5-turbo-16k": 0.000002,
    "gpt-3.5-turbo-1106": 0.000002,
    "gpt-35-turbo-0613": 0.000002,
    "gpt-35-turbo": 0.000002,
    "gpt-4-0613": 0.00006,
    "gpt-4-32k-0613": 0.00012,
    "gpt-4-32k": 0.00012,
    "gpt-4-1106-preview": 0.00003,
    "gpt-4-0125-preview": 0.00003,
}

# used for azure
ENGINES = {
    "gpt-3.5-turbo-16k-0613": "gpt-35-turbo-16k",
    "gpt-4-0613": "gpt-4",
    "gpt-4-32k-0613": "gpt-4-32k",
}


def calc_cost(model_name, input_tokens, output_tokens):
    """
    Calculates the cost of a response from the openai API.

    Args:
    response (openai.ChatCompletion): The response from the API.

    Returns:
    float: The cost of the response.
    """
    cost = (
        MODEL_COST_PER_INPUT[model_name] * input_tokens
        + MODEL_COST_PER_OUTPUT[model_name] * output_tokens
    )
    logger.info(
        f"input_tokens={input_tokens}, output_tokens={output_tokens}, cost={cost:.2f}"
    )
    return cost


@retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
def call_chat(model_name_or_path, inputs, use_azure, temperature, top_p, **model_args):
    """
    Calls the openai API to generate completions for the given inputs.

    Args:
    model_name_or_path (str): The name or path of the model to use.
    inputs (str): The inputs to generate completions for.
    use_azure (bool): Whether to use the azure API.
    temperature (float): The temperature to use.
    top_p (float): The top_p to use.
    **model_args (dict): A dictionary of model arguments.
    """
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    try:
        if use_azure:
            response = openai.ChatCompletion.create(
                engine=ENGINES[model_name_or_path] if use_azure else None,
                messages=[
                    {"role": "system", "content": system_messages},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                top_p=top_p,
                **model_args,
            )
        else:
            response = openai.ChatCompletion.create(
                model=model_name_or_path,
                messages=[
                    {"role": "system", "content": system_messages},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                top_p=top_p,
                **model_args,
            )
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = calc_cost(response.model, input_tokens, output_tokens)
        return response, cost
    except openai.error.InvalidRequestError as e:
        if e.code == "context_length_exceeded":
            print("Context length exceeded")
            return None
        raise e


def gpt_tokenize(string: str, encoding) -> int:
    """Returns the number of tokens in a text string."""
    num_tokens = len(encoding.encode(string))
    return num_tokens


def claude_tokenize(string: str, api) -> int:
    """Returns the number of tokens in a text string."""
    num_tokens = api.count_tokens(string)
    return num_tokens


def openai_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Runs inference on a dataset using the openai API.

    Args:
    test_dataset (datasets.Dataset): The dataset to run inference on.
    model_name_or_path (str): The name or path of the model to use.
    output_file (str): The path to the output file.
    model_args (dict): A dictionary of model arguments.
    existing_ids (set): A set of ids that have already been processed.
    max_cost (float): The maximum cost to spend on inference.
    """
    encoding = tiktoken.encoding_for_model(model_name_or_path)
    test_dataset = test_dataset.filter(
        lambda x: gpt_tokenize(x["text"], encoding) <= MODEL_LIMITS[model_name_or_path],
        desc="Filtering",
        load_from_cache_file=False,
    )
    openai_key = os.environ.get("OPENAI_API_KEY", None)
    if openai_key is None:
        raise ValueError(
            "Must provide an api key. Expected in OPENAI_API_KEY environment variable."
        )
    openai.api_key = openai_key
    print(f"Using OpenAI key {'*' * max(0, len(openai_key)-5) + openai_key[-5:]}")
    use_azure = model_args.pop("use_azure", False)
    if use_azure:
        openai.api_type = "azure"
        openai.api_base = "https://pnlpopenai3.openai.azure.com/"
        openai.api_version = "2023-05-15"
    temperature = model_args.pop("temperature", 0.2)
    top_p = model_args.pop("top_p", 0.95 if temperature > 0 else 1)
    print(f"Using temperature={temperature}, top_p={top_p}")
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    total_cost = 0
    print(f"Filtered to {len(test_dataset)} instances")
    with open(output_file, "a+") as f:
        for datum in tqdm(test_dataset, desc=f"Inference for {model_name_or_path}"):
            instance_id = datum["instance_id"]
            if instance_id in existing_ids:
                continue
            output_dict = {"instance_id": instance_id}
            output_dict.update(basic_args)
            output_dict["text"] = f"{datum['text']}\n\n"
            response, cost = call_chat(
                output_dict["model_name_or_path"],
                output_dict["text"],
                use_azure,
                temperature,
                top_p,
            )
            completion = response.choices[0]["message"]["content"]
            total_cost += cost
            print(f"Total Cost: {total_cost:.2f}")
            output_dict["full_output"] = completion
            output_dict["model_patch"] = extract_diff(completion)
            print(json.dumps(output_dict), file=f, flush=True)
            if max_cost is not None and total_cost >= max_cost:
                print(f"Reached max cost {max_cost}, exiting")
                break


@retry(wait=wait_random_exponential(min=60, max=600), stop=stop_after_attempt(6))
def call_anthropic(
    inputs, anthropic, model_name_or_path, temperature, top_p, **model_args
):
    """
    Calls the anthropic API to generate completions for the given inputs.

    Args:
    inputs (str): The inputs to generate completions for.
    anthropic (Anthropic): The anthropic API object.
    model_name_or_path (str): The name or path of the model to use.
    temperature (float): The temperature to use.
    top_p (float): The top_p to use.
    model_args (dict): A dictionary of model arguments.
    """
    try:
        completion = anthropic.completions.create(
            model=model_name_or_path,
            max_tokens_to_sample=6000,
            prompt=inputs,
            temperature=temperature,
            top_p=top_p,
            **model_args,
        )
        response = completion.completion
        input_tokens = anthropic.count_tokens(inputs)
        output_tokens = anthropic.count_tokens(response)
        cost = calc_cost(model_name_or_path, input_tokens, output_tokens)
        return completion, cost
    except Exception as e:
        logger.error(e)
        logger.error(f"Inputs: {inputs}")
        traceback.print_exc()
        time.sleep(20)
        return None
    

@retry(wait=wait_random_exponential(min=60, max=600), stop=stop_after_attempt(6))
def call_anthropic_v2(
    inputs, anthropic, model_name_or_path, temperature, top_p, **model_args
):
    """
    Calls the anthropic API to generate completions for the given inputs.

    Args:
    inputs list(str): The inputs to generate completions for.
    anthropic (Anthropic): The anthropic API object.
    model_name_or_path (str): The name or path of the model to use.
    temperature (float): The temperature to use.
    top_p (float): The top_p to use.
    model_args (dict): A dictionary of model arguments.
    """
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    try:
        messages = [
            {"role": "user", "content": user_message},
        ]
        response = anthropic.messages.create(
            messages=messages,
            max_tokens=4096,
            model=model_name_or_path,
            temperature=temperature,
            top_p=top_p,
            system=system_messages,
        )
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = calc_cost(response.model, input_tokens, output_tokens)
        return response, cost
    except Exception as e:
        logger.error(e)
        logger.error(f"Inputs: {inputs}")
        traceback.print_exc()
        time.sleep(20)
        return None


def anthropic_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Runs inference on a dataset using the anthropic API.

    Args:
    test_dataset (datasets.Dataset): The dataset to run inference on.
    model_name_or_path (str): The name or path of the model to use.
    output_file (str): The path to the output file.
    model_args (dict): A dictionary of model arguments.
    existing_ids (set): A set of ids that have already been processed.
    max_cost (float): The maximum cost to spend on inference.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", None)
    if api_key is None:
        raise ValueError(
            "Must provide an api key. Expected in ANTHROPIC_API_KEY environment variable."
        )
    print(f"Using Anthropic key {'*' * max(0, len(api_key)-5) + api_key[-5:]}")
    anthropic = Anthropic(api_key=api_key)
    test_dataset = test_dataset.filter(
        lambda x: claude_tokenize(x["text"], anthropic)
        <= MODEL_LIMITS[model_name_or_path],
        desc="Filtering",
        load_from_cache_file=False,
    )
    temperature = model_args.pop("temperature", 0.2)
    top_p = model_args.pop("top_p", 0.95 if temperature > 0 else 1)
    print(f"Using temperature={temperature}, top_p={top_p}")
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    total_cost = 0
    print(f"Filtered to {len(test_dataset)} instances")
    if 'claude-3' in model_name_or_path.lower():
        call_api = call_anthropic_v2
    else:
        call_api = call_anthropic
    with open(output_file, "a+") as f:
        for datum in tqdm(test_dataset, desc=f"Inference for {model_name_or_path}"):
            instance_id = datum["instance_id"]
            if instance_id in existing_ids:
                continue
            output_dict = {"instance_id": instance_id}
            output_dict.update(basic_args)
            if 'claude-3' in model_name_or_path.lower():
                output_dict["text_inputs"] = f"{datum['text']}\n"
            else:
                output_dict[
                    "text_inputs"
                ] = f"{HUMAN_PROMPT} {datum['text']}\n\n{AI_PROMPT}"
            try:
                completion, cost = call_api(
                    output_dict["text_inputs"],
                    anthropic,
                    model_name_or_path,
                    temperature,
                    top_p,
                    **model_args,
                )
            except Exception as e:
                logger.error(e)
                traceback.print_exc()
                continue
            total_cost += cost
            print(f"Total Cost: {total_cost:.2f}")
            if "claude-3" in model_name_or_path.lower():
                output_dict["full_output"] = completion.content[0].text
            else:
                output_dict["full_output"] = completion.completion
            output_dict["model_patch"] = extract_diff(output_dict["full_output"])
            print(json.dumps(output_dict), file=f, flush=True)
            if max_cost is not None and total_cost >= max_cost:
                print(f"Reached max cost {max_cost}, exiting")
                break


def parse_model_args(model_args):
    """
    Parses a string of model arguments and returns a dictionary of keyword arguments.

    Args:
        model_args (str): A string of comma-separated key-value pairs representing model arguments.

    Returns:
        dict: A dictionary of keyword arguments parsed from the input string.
    """
    kwargs = dict()
    if model_args is not None:
        for arg in model_args.split(","):
            key, value = arg.split("=")
            # infer value type
            if value in {"True", "False"}:
                kwargs[key] = value == "True"
            elif value.isnumeric():
                kwargs[key] = int(value)
            elif value.replace(".", "", 1).isnumeric():
                kwargs[key] = float(value)
            elif value in {"None"}:
                kwargs[key] = None
            elif value in {"[]"}:
                kwargs[key] = []
            elif value in {"{}"}:
                kwargs[key] = {}
            elif value.startswith("'") and value.endswith("'"):
                kwargs[key] = value[1:-1]
            elif value.startswith('"') and value.endswith('"'):
                kwargs[key] = value[1:-1]
            else:
                kwargs[key] = value
    return kwargs


def main(
    dataset_name_or_path,
    split,
    model_name_or_path,
    shard_id,
    num_shards,
    output_dir,
    model_args,
    max_cost,
):
    if shard_id is None and num_shards is not None:
        logger.warning(
            f"Received num_shards={num_shards} but shard_id is None, ignoring"
        )
    if shard_id is not None and num_shards is None:
        logger.warning(f"Received shard_id={shard_id} but num_shards is None, ignoring")
    model_args = parse_model_args(model_args)
    model_nickname = model_name_or_path
    if "checkpoint" in Path(model_name_or_path).name:
        model_nickname = Path(model_name_or_path).parent.name
    else:
        model_nickname = Path(model_name_or_path).name
    output_file = f"{model_nickname}__{dataset_name_or_path.split('/')[-1]}__{split}"
    if shard_id is not None and num_shards is not None:
        output_file += f"__shard-{shard_id}__num_shards-{num_shards}"
    output_file = Path(output_dir, output_file + ".jsonl")
    logger.info(f"Will write to {output_file}")
    existing_ids = set()
    if os.path.exists(output_file):
        with open(output_file) as f:
            for line in f:
                data = json.loads(line)
                instance_id = data["instance_id"]
                existing_ids.add(instance_id)
    logger.info(f"Read {len(existing_ids)} already completed ids from {output_file}")
    if Path(dataset_name_or_path).exists():
        dataset = load_from_disk(dataset_name_or_path)
    else:
        dataset = load_dataset(dataset_name_or_path)
    if not split in dataset:
        raise ValueError(f"Invalid split {split} for dataset {dataset_name_or_path}")
    dataset = dataset[split]
    lens = np.array(list(map(len, dataset["text"])))
    dataset = dataset.select(np.argsort(lens))
    if len(existing_ids) > 0:
        dataset = dataset.filter(
            lambda x: x["instance_id"] not in existing_ids,
            desc="Filtering out existing ids",
            load_from_cache_file=False,
        )
    if shard_id is not None and num_shards is not None:
        dataset = dataset.shard(num_shards, shard_id, contiguous=True)
    inference_args = {
        "test_dataset": dataset,
        "model_name_or_path": model_name_or_path,
        "output_file": output_file,
        "model_args": model_args,
        "existing_ids": existing_ids,
        "max_cost": max_cost,
    }
    if model_name_or_path.startswith("claude"):
        anthropic_inference(**inference_args)
    elif model_name_or_path.startswith("gpt"):
        openai_inference(**inference_args)
    else:
        raise ValueError(f"Invalid model name or path {model_name_or_path}")
    logger.info(f"Done!")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset_name_or_path",
        type=str,
        required=True,
        help="HuggingFace dataset name or local path",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split to use",
    )
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        help="Name of API model. Update MODEL* constants in this file to add new models.",
        choices=sorted(list(MODEL_LIMITS.keys())),
    )
    parser.add_argument(
        "--shard_id",
        type=int,
        default=None,
        help="Shard id to process. If None, process all shards.",
    )
    parser.add_argument(
        "--num_shards",
        type=int,
        default=None,
        help="Number of shards. If None, process all shards.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        required=True,
        help="Path to the output file.",
    )
    parser.add_argument(
        "--model_args",
        type=str,
        default=None,
        help="List of model arguments separated by commas. (e.g. 'top_p=0.95,temperature=0.70')",
    )
    parser.add_argument(
        "--max_cost",
        type=float,
        default=None,
        help="Maximum cost to spend on inference.",
    )
    args = parser.parse_args()
    main(**vars(args))
