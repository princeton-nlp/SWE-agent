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

from git import InvalidGitRepositoryError, Repo

LOGGER_NAME = "intercode"
START_UP_DELAY = 5
TIMEOUT_DURATION = 25
GITHUB_ISSUE_URL_PATTERN = re.compile(r'github\.com\/(.*?)\/(.*?)\/issues\/(\d+)')
GITHUB_REPO_URL_PATTERN = re.compile(r'.*[/@]?github\.com\/([^/]+)\/([^/]+)')

logger = logging.getLogger(LOGGER_NAME)


def get_data_path_name(data_path: str) -> str:
    """ if data_path is a file, return the file stem
    elif it's a github url, return the owner__repo_name
    """
    if data_path.startswith("text://"):
        return hashlib.sha256(data_path.removeprefix("text://").encode()).hexdigest()[:6]
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


# todo: Why not just use copy_anything_to_container?
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


def copy_anything_to_container(container, host_path: str, container_path: str) -> None:
    """Copy files or directories from host to container
    
    Note: Will need to set ownership on the copied files in the container.
    """
    if not Path(host_path).exists():
        msg = f"Path {host_path} does not exist, cannot copy it to container."
        raise FileNotFoundError(msg)
    cmd = ["docker", "cp", host_path, f"{container.id}:{container_path}"]
    logger.debug(f"Copying {host_path} to container at {container_path} with command: {shlex.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        msg = f"Error copying {host_path} to container at {container_path}: {e}"
        raise RuntimeError(msg) from e


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


PROCESS_DONE_MARKER_START = "///PROCESS-DONE:"
PROCESS_DONE_MARKER_END= ":PROCESS-DONE///"
PROCESS_DONE_REGEX = re.compile(rf"{PROCESS_DONE_MARKER_START}(.+?){PROCESS_DONE_MARKER_END}")


def read_with_timeout_experimental(container, timeout_duration):
    """
    Read data from a subprocess with a timeout.
    This function uses a file descriptor to read data from the subprocess in a non-blocking way.

    NOTE: This is an experimental implementation that is faster than `read_with_timeout`, but
    has not been thoroughly tested.

    Args:
        container (subprocess.Popen): The subprocess container.
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
        ready_to_read, _, _ = select.select([fd], [], [], 0.01)
        if ready_to_read:
            data = os.read(fd, 4096)
            if data:
                buffer += data
        if PROCESS_DONE_MARKER_START in buffer.decode():
            break
        time.sleep(0.01)  # Prevents CPU hogging

    if container.poll() is not None:
        raise RuntimeError("Subprocess exited unexpectedly.\nCurrent buffer: {}".format(buffer.decode()))
    if time.time() >= end_time:
        raise TimeoutError("Timeout reached while reading from subprocess.\nCurrent buffer: {}".format(buffer.decode()))
    decoded = buffer.decode()
    body = "\n".join(line for line in decoded.splitlines() if not line.startswith(PROCESS_DONE_MARKER_START))
    last_line = decoded.splitlines()[-1]
    _results = PROCESS_DONE_REGEX.search(last_line)
    if _results is None:
        raise ValueError(f"Could not find process done marker in last line: {last_line=}, {body=}")
    exit_code = _results.group(1)
    return body, exit_code


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
    output = read_with_timeout(container, lambda: list(), timeout_duration=2)
    if output:
        logger.error(f"Unexpected container setup output: {output}")
    return container, {"1", } # bash PID is always 1 for non-persistent containers


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
    output = read_with_timeout(container, lambda: list(), timeout_duration=2)
    if output:
        logger.error(f"Unexpected container setup output: {output}")
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
        docker_not_runnnig = any((
            "connection aborted" in str(e).lower(), 
            "connection refused" in str(e).lower(),
            "error while fetching server api version" in str(e).lower(),
        ))
        if docker_not_runnnig:
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


class InstanceBuilder:
    def __init__(self, token: Optional[str] = None):
        """This helper class is used to build the data for an instance object, 
        retrieving problem statements from github issues or local files and setting
        repo paths from github urls or local paths.
        """
        # Args that will be passed to the Instance constructor
        self.args = {}
        self.token = token
        self._instance_id_problem_suffix = ""

    def set_problem_statement_from_gh_issue(self, issue_url: str):
        owner, repo, issue_number = parse_gh_issue_url(issue_url)
        self.args["problem_statement"] = get_problem_statement_from_github_issue(owner, repo, issue_number, token=self.token)
        self.args["instance_id"] = f"{owner}__{repo}-i{issue_number}"
        self.args["problem_statement_source"] = "online"
    
    def set_problem_statement_from_file(self, file_path: str):
        self.set_problem_statement_from_text(Path(file_path).read_text())

    def set_problem_statement_from_text(self, text: str):
        self.args["problem_statement"] = text
        self.args["instance_id"] = hashlib.sha256(self.args["problem_statement"].encode()).hexdigest()[:6]
        self.args["problem_statement_source"] = "local"
    
    def set_problem_statement(self, data_path: str ):
        """Get problem statement for a single instance from a github issue url or a 
        path to a markdown or text file.
        """
        if data_path.startswith("text://"):
            return self.set_problem_statement_from_text(data_path.removeprefix("text://"))
        if is_github_issue_url(data_path):
            return self.set_problem_statement_from_gh_issue(data_path)
        if Path(data_path).is_file():
            return self.set_problem_statement_from_file(data_path)
        msg = f"Not sure how to get problem statement from {data_path=}."
        raise ValueError(msg)
    
    def set_repo_info_from_gh_url(self, url: str, base_commit: Optional[str] = None):
        owner, repo = parse_gh_repo_url(url)
        self.args["repo"] = f"{owner}/{repo}"
        self.args["repo_type"] = "github"
        if base_commit:
            self.args["base_commit"] = base_commit
        else:
            api = GhApi(token=self.token)
            self.args["base_commit"] = get_commit(api, owner, repo, base_commit).sha
        self.args["version"] = self.args["base_commit"][:7]
    
    def set_repo_info_from_local_path(self, path: str, base_commit: Optional[str] = None):
        self.args["repo"] = str(Path(path).resolve())
        self.args["repo_type"] = "local"
        if base_commit:
            self.args["base_commit"] = base_commit
        else:
            try:
                repo = Repo(path, search_parent_directories=True)
            except InvalidGitRepositoryError as e:
                msg = f"Could not find git repository at {path=}."
                raise ValueError(msg) from e
            if repo.is_dirty():
                msg = f"Local git repository {path} is dirty. Please commit or stash changes."
                raise ValueError(msg)
            self.args["base_commit"] = repo.head.object.hexsha
        self.args["version"] = self.args["base_commit"][:7]
    
    def set_repo_info(self, repo: str, base_commit: Optional[str] = None):
        if is_github_repo_url(repo):
            self.set_repo_info_from_gh_url(repo, base_commit=base_commit)
        elif Path(repo).is_dir():
            self.set_repo_info_from_local_path(repo, base_commit=base_commit)
        else:
            raise ValueError(f"Could not determine repo path from {repo=}.")
    
    def set_from_dict(self, instance_dict: Dict[str, Any]):
        self.args |= instance_dict
    
    def set_missing_fields(self):
        # todo: This field is only needed while swe_env is using some questionable logic
        # to determine whether to clone from a mirror or not. This should be removed in the future.
        # Values: 'swe-bench' (loaded from json/jsonl for swe-bench style inference),
        # 'online' (loaded from github issue or similar) or 'local' (loaded from local file)
        if "problem_statement_source" not in self.args:
            self.args["problem_statement_source"] = "swe-bench"
        if "repo_type" not in self.args: 
            self.args["repo_type"] = "github"
    
    def validate(self):
        required_fields = [
            "problem_statement",
            "instance_id",
            "repo",
            "repo_type",
            "base_commit",
            "version",
            "problem_statement_source",
        ]
        if not all(x in self.args for x in required_fields):
            missing = set(required_fields) - set(self.args.keys())
            raise ValueError(f"Missing required fields: {missing=}")
        if self.args["repo_type"] not in {"github", "local"}:
            raise ValueError(f"Invalid repo type: {self.args['repo_type']=}")
        if self.args["repo_type"] == "github" and self.args["repo"].count("/") != 1:
            raise ValueError(f"Invalid repo format for {self.args['repo_type']=}: {self.args['repo']=}")
    
    def build(self) -> Dict[str, Any]:
        self.set_missing_fields()
        self.validate()
        return self.args
    

def get_instances(
        file_path: str, 
        base_commit: Optional[str] = None, 
        split: Optional[str] = None, 
        token: Optional[str] = None,
        *,
        repo_path: str = "",
    ) -> List[Dict[str, Any]]:
    """
    Getter function for handling json, jsonl files

    Args:
        file_path (str): Path to file

    Returns:
        List of instances as dictionaries
    """
    def instance_from_dict(instances):
        ib = InstanceBuilder(token=token)
        ib.set_from_dict(instances)
        return ib.build()

    def postproc_instance_list(instances):
        if isinstance(instances, dict):
            msg = "Expected a list of instances, got a dictionary."
            raise ValueError(msg)
        return [instance_from_dict(x) for x in instances]


    # If file_path is a directory, attempt load from disk
    if os.path.isdir(file_path):
        try:
            dataset_or_dict = load_from_disk(file_path)
            if isinstance(dataset_or_dict, dict):
                return postproc_instance_list(dataset_or_dict[split])
            return postproc_instance_list(dataset_or_dict)
        except FileNotFoundError:
            # Raised by load_from_disk if the directory is not a dataset directory
            pass

    # The next if statement is very brittle logic to determine if we're processing a single instance
    if file_path.startswith("text://") or (Path(file_path).is_file() and Path(file_path).suffix in ['.md', '.txt']):
        ib = InstanceBuilder(token=token)
        ib.set_problem_statement(file_path)
        if repo_path:
            ib.set_repo_info(repo_path, base_commit=base_commit)
        elif is_github_repo_url(file_path):
            ib.set_repo_info_from_gh_url(file_path)
        else:
            raise ValueError(f"Could not determine repo path from {file_path=}, {repo_path=}")

        return [ib.build()]
    
    if base_commit is not None:
        raise ValueError("base_commit must be None if data_path is not a github issue url")

    # If file_path is a file, load the file
    if file_path.endswith(".json"):
        return postproc_instance_list(json.load(open(file_path)))
    if file_path.endswith(".jsonl"):
        return postproc_instance_list([json.loads(x) for x in open(file_path, 'r').readlines()])

    if repo_path:
        msg = "repo_path must be empty if data_path is not a github url or local repo url"
        raise ValueError(msg)

    # Attempt load from HF datasets as a last resort
    try:
        return postproc_instance_list(load_dataset(file_path, split=split))
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

