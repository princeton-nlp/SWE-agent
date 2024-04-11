import hashlib
import shlex
import docker
import json
import logging
import os
import re
import select
import signal
import subprocess
import tarfile
import tempfile
import time
import traceback

from datasets import load_dataset, load_from_disk
from ghapi.all import GhApi
from io import BytesIO
from pathlib import Path
from subprocess import PIPE, STDOUT
from typing import Any, List, Optional, Set, Tuple, Dict

LOGGER_NAME = "intercode"
START_UP_DELAY = 5
TIMEOUT_DURATION = 25
GITHUB_ISSUE_URL_PATTERN = re.compile(r'github\.com\/(.*?)\/(.*?)\/issues\/(\d+)')
GITHUB_REPO_URL_PATTERN = re.compile(r'.*[/@]?github\.com\/([^/]+)\/([^/]+)')

logger = logging.getLogger(LOGGER_NAME)


def get_data_path_name(data_path: str):
    """ if data_path is a file, return the file stem
    elif it's a github url, return the owner__repo_name
    """
    match = GITHUB_ISSUE_URL_PATTERN.search(data_path)
    if match:
        owner, repo, _ = match.groups()
        return f"{owner}__{repo}"
    return Path(data_path).stem


def is_github_issue_url(data_path: str) -> bool:
    """Check if data_path is an URL pointing to a github issue"""
    return GITHUB_ISSUE_URL_PATTERN.search(data_path) is not None


def is_github_repo_url(data_path: str) -> bool:
    """Check if data_path is an URL pointing to a github repository.
    Paths to issues or PRs will also match this pattern.
    """
    return GITHUB_REPO_URL_PATTERN.search(data_path) is not None


def copy_file_to_container(container, contents, container_path):
    """
    Copies a given string into a Docker container at a specified path.

    Args:
    - container: Docker SDK container object.
    - contents: The string to copy into the container.
    - container_path: The path inside the container where the string should be copied to.

    Returns:
    - None
    """
    temp_file_name = None

    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_name = temp_file.name
            # Write the string to the temporary file and ensure it's written to disk
            temp_file.write(contents.encode('utf-8'))
            temp_file.flush()
            os.fsync(temp_file.fileno())

        # Create a TAR archive in memory containing the temporary file
        with tempfile.NamedTemporaryFile():
            with open(temp_file_name, 'rb') as temp_file:
                # Prepare the TAR archive
                with BytesIO() as tar_stream:
                    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                        tar_info = tarfile.TarInfo(name=os.path.basename(container_path))
                        tar_info.size = os.path.getsize(temp_file_name)
                        tar.addfile(tarinfo=tar_info, fileobj=temp_file)
                    tar_stream.seek(0)
                    # Copy the TAR stream to the container
                    container.put_archive(path=os.path.dirname(container_path), data=tar_stream.read())

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Cleanup: Remove the temporary file if it was created
        if temp_file_name and os.path.exists(temp_file_name):
            os.remove(temp_file_name)


def read_with_timeout(container, pid_func, timeout_duration):
    """
    Read data from a subprocess with a timeout.
    This function uses a file descriptor to read data from the subprocess in a non-blocking way.

    Args:
        container (subprocess.Popen): The subprocess container.
        pid_func (function): A function that returns a list of process IDs (except the PID of the main process).
        timeout_duration (int): The timeout duration in seconds.

    Returns:
        str: The data read from the subprocess, stripped of trailing newline characters.

    Raises:
        TimeoutError: If the timeout duration is reached while reading from the subprocess.
    """
    buffer = b""
    fd = container.stdout.fileno()
    end_time = time.time() + timeout_duration

    while time.time() < end_time:
        pids = pid_func()
        if len(pids) > 0:
            # There are still PIDs running
            time.sleep(0.05)
            continue
        ready_to_read, _, _ = select.select([fd], [], [], 0.1)
        if ready_to_read:
            data = os.read(fd, 4096)
            if data:
                buffer += data
        else:
            # No more data to read
            break
        time.sleep(0.05)  # Prevents CPU hogging

    if container.poll() is not None:
        raise RuntimeError("Subprocess exited unexpectedly.\nCurrent buffer: {}".format(buffer.decode()))
    if time.time() >= end_time:
        raise TimeoutError("Timeout reached while reading from subprocess.\nCurrent buffer: {}\nRunning PIDs: {}".format(buffer.decode(), pids))
    return buffer.decode()


class timeout:
    def __init__(self, seconds=TIMEOUT_DURATION, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def get_background_pids(container_obj):
    pids = (
        container_obj.exec_run("ps -eo pid,comm --no-headers")
        .output.decode()
        .split("\n")
    )
    pids = [x.split() for x in pids if x]
    pids = [x for x in pids if x[1] not in {"ps"} and x[0] != "1"]
    bash_pids = [x for x in pids if x[1] == "bash"]
    other_pids = [x for x in pids if x[1] not in {"bash"}]
    return bash_pids, other_pids


def _get_non_persistent_container(ctr_name: str, image_name: str) -> Tuple[subprocess.Popen, set]:
    startup_cmd = [
        "docker",
        "run",
        "-i",
        "--rm",
        "--name",
        ctr_name,
        image_name,
        "/bin/bash",
        "-l",
        "-m",
    ]
    logger.debug(f"Starting container with command: %s", shlex.join(startup_cmd))
    container = subprocess.Popen(
        startup_cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        bufsize=1, # line buffered
    )
    time.sleep(START_UP_DELAY)
    # try to read output from container setup (usually an error), timeout if no output
    try:
        with timeout(seconds=2):
            output = container.stdout.read()
            if output:
                logger.error(f"Unexpected container setup output: {output}")
    except TimeoutError:
        pass
    return container, {"1", }  # bash PID is always 1 for non-persistent containers


def _get_persistent_container(ctr_name: str, image_name: str, persistent: bool = False) -> Tuple[subprocess.Popen, Set]:
    client = docker.from_env()
    containers = client.containers.list(all=True, filters={"name": ctr_name})
    if ctr_name in [c.name for c in containers]:
        container_obj = client.containers.get(ctr_name)
        if container_obj.status in {"created"}:
            container_obj.start()
        elif container_obj.status in {"running"}:
            pass
        elif container_obj.status in {"exited"}:
            container_obj.restart()
        elif container_obj.status in {"paused"}:
            container_obj.unpause()
        else:
            raise RuntimeError(f"Unexpected container status: {container_obj.status}")
    else:
        container_obj = client.containers.run(
            image_name,
            command='/bin/bash -l -m',
            name=ctr_name,
            stdin_open=True,
            tty=True,
            detach=True,
            auto_remove=not persistent,
        )
        container_obj.start()
    startup_cmd =  [
        "docker",
        "exec",
        "-i",
        ctr_name,
        "/bin/bash",
        "-l",
        "-m",
    ]
    logger.debug(f"Starting container with command: %s", shlex.join(startup_cmd))
    container = subprocess.Popen(
        startup_cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        bufsize=1, # line buffered
    )
    time.sleep(START_UP_DELAY)
    # try to read output from container setup (usually an error), timeout if no output
    try:
        with timeout(seconds=2):
            output = container.stdout.read()
            if output:
                logger.error(f"Unexpected container setup output: {output}")
    except TimeoutError:
        pass
    # Get the process IDs of the container
    # There should be at least a head process and possibly one child bash process
    bash_pids, other_pids = get_background_pids(container_obj)
    bash_pid = 1
    if len(bash_pids) == 1:
        bash_pid = bash_pids[0][0]
    elif len(bash_pids) > 1 or len(other_pids) > 0:
        raise RuntimeError(f"Detected alien processes attached or running. Please ensure that no other agents are running on this container. PIDs: {bash_pids}, {other_pids}")
    return container, set(map(str, [bash_pid, 1, ]))


def get_container(ctr_name: str, image_name: str, persistent: bool = False) -> Tuple[subprocess.Popen, Set]:
    """
    Get a container object for a given container name and image name

    Arguments:
        ctr_name (str): Name of container
        image_name (str): Name of image
        persistent (bool): Whether to use a persistent container or not
    Returns:
        Container object
    """
    # Let's first check that the image exists and give some better error messages
    try:
        client = docker.from_env()
    except docker.errors.DockerException as e:
        if "connection aborted" in str(e).lower() or "connection refused" in str(e).lower():
            msg = (
                "Probably the Docker daemon is not running. Please start the Docker daemon and try again. "
                "You might need to allow the use of the docker socket "
                "(https://github.com/princeton-nlp/SWE-agent/issues/159) or symlink the socket "
                "if it's at a non-standard location "
                "(https://github.com/princeton-nlp/SWE-agent/issues/20#issuecomment-2047506005)."
            )
            raise RuntimeError(msg) from e
        raise
    filterred_images = client.images.list(filters={'reference': image_name})
    if len(filterred_images) == 0:
        msg = (
            f"Image {image_name} not found. Please ensure it is built and available. "
            "Please double-check that you followed all installation/setup instructions from the "
            "readme."
        )
        raise RuntimeError(msg)
    elif len(filterred_images) > 1:
        logger.warning(f"Multiple images found for {image_name}, that's weird.")
    attrs = filterred_images[0].attrs 
    if attrs is not None:
        logger.info(
            f"Found image {image_name} with tags: {attrs['RepoTags']}, created: {attrs['Created']} "
            f"for {attrs['Os']} {attrs['Architecture']}."
        )

    if persistent:
        return _get_persistent_container(ctr_name, image_name)
    else:
        return _get_non_persistent_container(ctr_name, image_name)


def get_commit(api: GhApi, owner: str, repo: str, base_commit: str = None):
    if base_commit:
        commit = api.repos.get_commit(owner, repo, base_commit)
    else:
        commit = api.repos.list_commits(owner, repo)[0]
    return commit



class InvalidGithubURL(ValueError):
    ...


def parse_gh_issue_url(issue_url: str) -> Tuple[str, str, str]:
    """Return owner, repo, issue number from issue url"""
    match = GITHUB_ISSUE_URL_PATTERN.search(issue_url)
    if not match:
        raise InvalidGithubURL(f"Invalid GitHub issue URL: {issue_url}")
    res = match.groups()
    assert len(res) == 3
    return tuple(res)  # type: ignore


def parse_gh_repo_url(repo_url: str) -> Tuple[str, str]:
    """Return owner, repo from repo url"""
    match = GITHUB_REPO_URL_PATTERN.search(repo_url)
    if not match:
        raise InvalidGithubURL(f"Invalid GitHub issue URL: {repo_url}")
    res = match.groups()
    assert len(res) == 2
    return tuple(res)  # type: ignore


def get_gh_issue_data(issue_url: str, *, token: str = ""):
    """Returns github issue data in the form of a dictionary.
    See https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#get-an-issue
    for return format
    """
    owner, repo, issue_number = parse_gh_issue_url(issue_url)
    api = GhApi(token=token)
    return api.issues.get(owner, repo, issue_number)



def get_problem_statement_from_github_issue(owner: str, repo: str, issue_number: str, *, token: Optional[str] = "") -> str:
    """Return problem statement from github issue"""
    api = GhApi(token=token)
    issue = api.issues.get(owner, repo, issue_number)
    title = issue.title if issue.title else ""
    body = issue.body if issue.body else ""
    return f"{title}\n{body}\n"


def get_instance_from_github_url(url: str, *, base_commit: Optional[str]=None, problem_statement: str="", token: Optional[str] = None) -> dict[str, Any]:
    """Get instance from a github URL (either issue or repo)"""
    try: 
        owner, repo, issue_number = parse_gh_issue_url(url)
    except InvalidGithubURL:
        owner, repo = parse_gh_repo_url(url)
        issue_number = None
    record = dict()
    record["repo"] = f"{owner}/{repo}"
    if base_commit:
        record["base_commit"] = base_commit
    else:
        api = GhApi(token=token)
        record["base_commit"] = get_commit(api, owner, repo, base_commit).sha
    record["version"] = record["base_commit"][:7]
    if not problem_statement:
        if not issue_number:
            msg = "Problem statement must be provided if data_path is a github repo url without an issue number."
            raise ValueError(msg)
        record["problem_statement"] = get_problem_statement_from_github_issue(owner, repo, issue_number, token=token)
    else:
        record["problem_statement"] = problem_statement
    if issue_number is not None:
        record["instance_id"] = f"{owner}__{repo}-i{issue_number}"
    else:
        # Get a unique ID by hashing the problem statement
        ps_hash = hashlib.sha256(problem_statement.encode()).hexdigest()[:6]
        record["instance_id"] = f"{owner}__{repo}-{ps_hash}"
    return record


def get_instances(
        file_path: str, 
        base_commit: Optional[str] = None, 
        split: Optional[str] = None, 
        token: Optional[str] = None,
        *,
        problem_statement: str = "",
    ):
    """
    Getter function for handling json, jsonl files

    Args:
        file_path (str): Path to file
        problem_statement: Problem statement when running on github repository URL
            or local path. If running on github issue, will replace issue content.

    Returns:
        List of instances
    """
    # If file_path is a directory, attempt load from disk
    if os.path.isdir(file_path):
        dataset_or_dict = load_from_disk(file_path)
        if isinstance(dataset_or_dict, dict):
            return dataset_or_dict[split]
        return dataset_or_dict

    # If file_path is a github issue url, fetch the issue and return a single instance
    if is_github_repo_url(file_path):
        record = get_instance_from_github_url(file_path, base_commit=base_commit, problem_statement=problem_statement, token=token)
        return [record,]
    
    if base_commit is not None:
        raise ValueError("base_commit must be None if data_path is not a github issue url")

    # If file_path is a file, load the file
    if file_path.endswith(".json"):
        return json.load(open(file_path))
    if file_path.endswith(".jsonl"):
        return [json.loads(x) for x in open(file_path, 'r').readlines()]

    if problem_statement:
        msg = "problem_statement must be empty if data_path is not a github url or local repo url"
        raise ValueError(msg)

    # Attempt load from HF datasets as a last resort
    try:
        return load_dataset(file_path, split=split)
    except:
        raise ValueError(
            f"Could not load instances from {file_path}. "
            "Please ensure --data_path is a GitHub URL, a SWE-bench HuggingFace dataset, or a JSON/JSONL file."
        )


def get_associated_commit_urls(org: str, repo: str, issue_number: str, *, token: str = "") -> list[str]:
    """Return the URLs of commits that would close an issue."""
    api = GhApi(token=token)
    # Strangely the "pull_request" field of api.issues.get is often not set
    # so we have to go through the events to check if there's a commit
    events = api.issues.list_events(org, repo, issue_number)
    commit_urls = []
    for event in events:
        if not event.event == "referenced":
            continue
        if not event.commit_id:
            continue
        commit = api.repos.get_commit(org, repo, event.commit_id)
        message = commit.commit.message
        if f"fixes #{issue_number}" in message.lower() or f"closes #{issue_number}" in message.lower():
            commit_urls.append(commit.html_url)
    return commit_urls


def remove_triple_backticks(text: str) -> str:
    return "\n".join(line.removeprefix("```") for line in text.splitlines())

_MARKDOWN_TRAJECTORY_EMOJI_MAPPING = {
    "observation": "👀",
    "response": "️🧑‍🚒",
    "state": "🧠",
    "thought": "💡",

}
def format_trajectory_markdown(trajectory: List[Dict[str, str]]):
    """Format a trajectory as a markdown string for use in gh PR description."""
    prefix = [
        "<details>",
        "<summary>Thought process ('trajectory') of SWE-agent (click to expand)</summary>",
        "",
        "",
    ]
    steps = []
    for i, step in enumerate(trajectory):
        step_strs = []
        for key, value in step.items():
            emoji = _MARKDOWN_TRAJECTORY_EMOJI_MAPPING.get(key, "")
            if emoji:
                emoji += " "
            step_strs.append(f"**{emoji}{key.capitalize()} ({i})**:")
            if key in ["observation", "state", "action"]:
                step_strs.append("```")
                step_strs.append(remove_triple_backticks(value).strip())
                step_strs.append("```")
            else:
                step_strs.append(value.strip())
        steps.append("\n".join(step_strs))
    suffix = [
        "",
        "</details>",
    ] 
    return "\n".join(prefix) + "\n\n---\n\n".join(steps) + "\n".join(suffix)