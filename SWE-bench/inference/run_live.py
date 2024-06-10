#!/usr/bin/env python3

"""
This module contains functions for running a live inference session on a GitHub issue.
It clones the repository associated with the issue, builds a BM25 retrieval index, and
generates a prompt for the user to interact with the model. The output is saved to a
specified directory.
"""
import json
import subprocess
from pathlib import Path
from ghapi.all import GhApi
import os
import re
import time
from datetime import datetime
from tqdm.auto import tqdm
from make_datasets.utils import ContextManager, string_to_bool, extract_diff, extract_minimal_patch
from make_datasets.bm25_retrieval import (
    make_index,
    clone_repo,
    search,
    DOCUMENT_ENCODING_FUNCTIONS,
)
from make_datasets.create_instance import (
    PROMPT_FUNCTIONS,
    TOKENIZER_FUNCS,
    make_code_text,
    ingest_files,
)
from run_api import call_chat, call_anthropic
import logging
from argparse import ArgumentParser

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_problem_statement(owner, repo, issue_num, ghapi, include_comments=False):
    issue = ghapi.issues.get(owner, repo, issue_num)
    issue_text = "\n".join([issue.title, issue.body])
    # Solved issues may include comments that give answers away too much
    if include_comments:
        all_comments = list(ghapi.issues.list_comments(owner, repo, issue_num))
        comments = [comment.body for comment in all_comments]
        comment_text = "Comment: " if comments else "" + "\nComment:".join(comments)
        issue_text += "\n" + comment_text
    return issue_text


def get_readme_files(repo_path):
    files = list(Path(repo_path).iterdir())
    files = list(filter(lambda x: x.is_file(), files))
    files = list(filter(lambda x: x.name.lower().startswith("readme"), files))
    if files:
        files = sorted(files, key=lambda x: len(x.name))
        files = [files[0]]
    return [Path(file).relative_to(repo_path).as_posix() for file in files]


def make_instance(
    owner,
    repo,
    query,
    commit,
    root_dir,
    token,
    document_encoding_func,
    python,
    instance_id,
    tokenizer,
    tokenizer_func,
    prompt_style,
    max_context_len,
    include_readmes,
):
    """
    Creates an instance for a given query and repository.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        query (str): The query to search for.
        commit (str): The commit hash to use.
        root_dir (str): The root directory to clone the repository to.
        token (str): The GitHub token to use for authentication.
        document_encoding_func (function): The function to use for encoding documents.
        python (str): The path to the Python executable.
        instance_id (int): The ID of the instance.
        tokenizer (str): The name of the tokenizer to use.
        tokenizer_func (function): The function to use for tokenization.
        prompt_style (str): The style of prompt to use.
        max_context_len (int): The maximum length of the context.
        include_readmes (bool): Whether to include README files in the instance.

    Returns:
        dict: The instance.
    """
    thread_id = 0
    instance = {"instance_id": instance_id, "problem_statement": query}
    logger.info(f"Cloning repo {owner}/{repo}")
    repo_dir = clone_repo(f"{owner}/{repo}", root_dir, token, False, thread_id)
    if commit is None:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir
        ).decode("utf-8").strip()
    logger.info(f"Buidling BM25 retrieval index for {owner}/{repo}@{commit}")
    index_dir = make_index(
        repo_dir,
        root_dir,
        commit,
        document_encoding_func,
        python,
        thread_id,
        instance_id,
    )
    results = search(instance, index_dir)
    hits = results["hits"]
    logger.info(f"Retrieved {len(hits)} documents")
    with ContextManager(repo_dir, commit) as cm:
        if include_readmes:
            readmes = get_readme_files(cm.repo_path)
        else:
            readmes = list()
        instance["readmes"] = ingest_files(readmes)
        for hit in hits:
            hit["file_contents"] = open(hit["docid"]).read()
        instance["file_contents"] = dict()
        base_text_inputs = PROMPT_FUNCTIONS[prompt_style](instance)
        base_text_input_length = len(tokenizer_func(base_text_inputs, tokenizer))
        instance["file_contents"] = {x["docid"]: x["file_contents"] for x in hits}
        cur_input_len = base_text_input_length
        include_files = list()
        for filename in [x["docid"] for x in hits]:
            content = make_code_text({filename: instance["file_contents"][filename]})
            tokens = tokenizer_func(content, tokenizer)
            if cur_input_len + len(tokens) < max_context_len:
                include_files.append(filename)
                cur_input_len += len(tokens)
        logger.info(
            f"Including {len(include_files)} files in context with {cur_input_len} tokens:\n"
            + "\n\t".join(sorted(include_files))
        )
        instance["file_contents"] = {
            filename: instance["file_contents"][filename] for filename in include_files
        }
        instance["text_inputs"] = PROMPT_FUNCTIONS[prompt_style](instance)
        return instance


def parse_issue_url(issue_url):
    issue_pat = re.compile(r"github\.com\/(.+?)\/(.+?)\/issues\/(\d+)")
    match = issue_pat.search(issue_url)
    if not match:
        raise ValueError(
            f"issue_url ({issue_url}) does not seem to be a valid issue url."
            + "\nPlease use url like https://github.com/owner/repo/issues/12345"
        )
    owner, repo, issue_num = match.groups()
    return owner, repo, issue_num


def main(
    model_name,
    prompt_style,
    issue_url,
    base_commit,
    max_context_length,
    document_encoding_func,
    output_dir,
    root_dir,
    include_readmes,
):
    if base_commit is not None and len(issue_url) != len(base_commit):
        raise ValueError(
            f"Must provide either no base commits or one base commit per issue url"
        )
    if base_commit is None:
        base_commit = [None] * len(issue_url)
    gh_token = os.environ.get("GITHUB_TOKEN", None)
    if gh_token is not None:
        logger.warning(f'Using GitHub token: {"*" * 8}{gh_token[-4:]}')
    gh = GhApi(token=gh_token)
    tokenizer, tokenizer_func = TOKENIZER_FUNCS["cl100k"]
    document_encoding_func = DOCUMENT_ENCODING_FUNCTIONS[document_encoding_func]
    python = subprocess.check_output(["which", "python"]).decode("utf-8").strip()
    outputs = list()
    for issue, commit in tqdm(zip(issue_url, base_commit), total=len(issue_url)):
        owner, repo, issue_num = parse_issue_url(issue)
        problem_statement = get_problem_statement(owner, repo, int(issue_num), gh)
        instance_id = f"{owner}__{repo}-{issue_num}"
        logger.info(f"Creating instance {instance_id}")
        instance = make_instance(
            owner,
            repo,
            problem_statement,
            commit,
            root_dir,
            gh_token,
            document_encoding_func,
            python,
            instance_id,
            tokenizer,
            tokenizer_func,
            prompt_style,
            max_context_length,
            include_readmes,
        )
        logger.info(f"Calling model {model_name}")
        start = time.time()
        if model_name.startswith("gpt"):
            import openai
            openai.api_key = os.environ.get("OPENAI_API_KEY", None)
            inputs = instance["text_inputs"]
            response, _ = call_chat(
                model_name, inputs, use_azure=False, temperature=0, top_p=1
            )
            completion = response.choices[0]["message"]["content"]
            logger.info(f'Generated {response.usage.completion_tokens} tokens in {(time.time() - start):.2f} seconds')
        else:
            from anthropic import Anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY", None)
            anthropic = Anthropic(api_key=api_key)
            response = call_anthropic(
                inputs, anthropic, model_name, temperature=0, top_p=1
            )
            completion = response.completion
        model_patch = extract_diff(completion)
        minimal_patch = extract_minimal_patch(model_patch)
        outputs.append(
            {
                "instance_id": instance_id,
                "response": completion,
                "problem_statement": problem_statement,
                "text_inputs": inputs,
                "model_patch": model_patch,
                "minimal_patch": minimal_patch,
            }
        )
    os.makedirs(output_dir, exist_ok=True)
    output_file = Path(
        output_dir,
        f'{model_name}__{prompt_style}__{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.jsonl',
    )
    with open(output_file, "+a") as f:
        for output in outputs:
            print(json.dumps(output), file=f, flush=True)
    logger.info(f"Wrote output to {output_file}")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model_name", type=str)
    parser.add_argument(
        "--prompt_style", type=str, choices=PROMPT_FUNCTIONS.keys(), default="style-3"
    )
    parser.add_argument("--issue_url", type=str, nargs="+")
    parser.add_argument("--base_commit", type=str, nargs="+")
    parser.add_argument("--max_context_length", type=int, default=16_000)
    parser.add_argument(
        "--document_encoding_func",
        type=str,
        choices=DOCUMENT_ENCODING_FUNCTIONS.keys(),
        default="file_name_and_contents",
    )
    parser.add_argument("--output_dir", type=str, default="./live_outputs")
    parser.add_argument("--root_dir", type=str, default="./run_live_data")
    parser.add_argument("--include_readmes", type=string_to_bool, default=False)
    args = parser.parse_args()
    main(**vars(args))
