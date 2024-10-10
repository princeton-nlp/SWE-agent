from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import tarfile
import tempfile
import time
import traceback
from io import BytesIO
from pathlib import Path
from subprocess import PIPE, STDOUT
from typing import Any, Callable

from datasets import load_dataset, load_from_disk
from ghapi.all import GhApi
from git import InvalidGitRepositoryError, Repo
from unidiff import PatchSet

import docker
import docker.types
from docker.models.containers import Container
from sweagent.utils.config import keys_config
from sweagent.utils.log import get_logger

DOCKER_START_UP_DELAY = float(keys_config.get("SWE_AGENT_DOCKER_START_UP_DELAY", 1))
DOCKER_COMPOSE_TERMINATION_DELAY = float(keys_config.get("SWE_AGENT_DOCKER_START_UP_DELAY", 100))
DOCKER_COMPOSE_STARTUP_DELAY = float(keys_config.get("SWE_AGENT_DOCKER_START_UP_DELAY", 600))
GITHUB_ISSUE_URL_PATTERN = re.compile(r"github\.com\/(.*?)\/(.*?)\/issues\/(\d+)")
GITHUB_REPO_URL_PATTERN = re.compile(r".*[/@]?github\.com\/([^/]+)\/([^/]+)")

CTF_CHALLENGES_CATEGORIES = {
    "rev": "reverse engineering",
    "pwn": "binary exploitation",
    "web": "web security",
    "crypto": "cryptography",
    "misc": "miscellaneous",
    "forensics": "forensics",
}

logger = get_logger("env_utils")


class NoOutputTimeoutError(TimeoutError): ...


def get_data_path_name(data_path: str) -> str:
    """if data_path is a file, return the file stem
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


# TODO: Why not just use copy_anything_to_container?
def copy_file_to_container(container: Container, contents: str, container_path: str) -> None:
    """
    Copies a given string into a Docker container at a specified path.

    Args:
        container: Docker SDK container object.
        contents: The string to copy into the container.
        container_path: The path inside the container where the string should be copied to.

    Returns:
        None
    """
    temp_file_name = None

    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_name = temp_file.name
            # Write the string to the temporary file and ensure it's written to disk
            temp_file.write(contents.encode("utf-8"))
            temp_file.flush()
            os.fsync(temp_file.fileno())

        # Create a TAR archive in memory containing the temporary file
        with tempfile.NamedTemporaryFile():
            with open(temp_file_name, "rb") as temp_file:
                # Prepare the TAR archive
                with BytesIO() as tar_stream:
                    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                        tar_info = tarfile.TarInfo(name=Path(container_path).name)
                        tar_info.size = Path(temp_file_name).stat().st_size
                        tar.addfile(tarinfo=tar_info, fileobj=temp_file)
                    tar_stream.seek(0)
                    # Copy the TAR stream to the container
                    container.put_archive(path=Path(container_path).parent, data=tar_stream.read())

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Cleanup: Remove the temporary file if it was created
        if temp_file_name and Path(temp_file_name).exists():
            os.remove(temp_file_name)


def copy_anything_to_container(container: Container, host_path: str, container_path: str) -> None:
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


def read_with_timeout(container: subprocess.Popen, pid_func: Callable, timeout_duration: int | float) -> str:
    """
    Read data from a subprocess with a timeout.
    This function uses a file descriptor to read data from the subprocess in a non-blocking way.

    Args:
        container: The subprocess container.
        pid_func: A function that returns a list of process IDs (except the PID of the main process).
        timeout_duration: The timeout duration in seconds.

    Returns:
        output: The data read from the subprocess, stripped of trailing newline characters.

    Raises:
        TimeoutError: If the timeout duration is reached while reading from the subprocess.
    """
    buffer = b""
    fd = container.stdout.fileno()
    end_time = time.time() + timeout_duration

    # Select is not available on windows
    is_windows = platform.system() == "Windows"
    if not is_windows:
        import select
    else:
        os.set_blocking(fd, False)

    def ready_to_read(fd) -> bool:
        if is_windows:
            # We can't do the extra check
            return True
        return bool(select.select([fd], [], [], 0.01)[0])

    while time.time() < end_time:
        pids = pid_func()
        if len(pids) > 0:
            # There are still PIDs running
            time.sleep(0.05)
            continue
        if ready_to_read(fd):
            data = os.read(fd, 4096)
            if data:
                buffer += data
        else:
            # No more data to read
            break
        time.sleep(0.05)  # Prevents CPU hogging

    if container.poll() is not None:
        msg = f"Subprocess exited unexpectedly.\nCurrent buffer: {buffer.decode()}"
        raise RuntimeError(msg)
    if time.time() >= end_time:
        msg = f"Timeout reached while reading from subprocess.\nCurrent buffer: {buffer.decode()}\nRunning PIDs: {pids}"
        raise TimeoutError(msg)

    decoded = buffer.decode("utf-8", errors="backslashreplace").replace("\r\n", "\n")
    return "\n".join(line for line in decoded.splitlines())


PROCESS_DONE_MARKER_START = "///PROCESS-DONE:"
PROCESS_DONE_MARKER_END = ":PROCESS-DONE///"
PROCESS_DONE_REGEX = re.compile(rf"{PROCESS_DONE_MARKER_START}(.+?){PROCESS_DONE_MARKER_END}")
DECODED_BUFFER_FAILURE_THRESHOLD = 0.1


def _check_for_too_many_non_unicode_bytes(buffer: bytes):
    number_of_failures = int(DECODED_BUFFER_FAILURE_THRESHOLD * len(buffer))
    start_byte = 0
    for _ in range(number_of_failures):
        try:
            buffer[start_byte:].decode()
            return
        except UnicodeDecodeError as e:
            start_byte = e.start + 1
    msg = "Too many non-unicode characters in output of command."
    raise UnicodeError(msg)


def read_with_timeout_experimental(
    container: subprocess.Popen, timeout_duration: int | float, no_output_timeout_duration: int | float
) -> tuple[str, str]:
    """
    Read data from a subprocess with a timeout.
    This function uses a file descriptor to read data from the subprocess in a non-blocking way.

    NOTE: This is an experimental implementation that is faster than `read_with_timeout`, but
    has not been thoroughly tested.

    Args:
        container: The subprocess container.
        timeout_duration: The timeout duration in seconds.
        no_output_timeout_duration: The timeout duration to wait if no output is produced, in seconds.

    Returns:
        Output and exit code, both as strings (!)

    Raises:
        TimeoutError: If the timeout duration is reached while reading from the subprocess.
    """
    buffer = b""
    fd = container.stdout.fileno()
    start_time = time.time()
    end_time = start_time + timeout_duration
    end_time_no_output = start_time + no_output_timeout_duration

    # Select is not available on windows
    is_windows = platform.system() == "Windows"
    if not is_windows:
        import select
    else:
        os.set_blocking(fd, False)

    def ready_to_read(fd) -> bool:
        if is_windows:
            # We can't do the extra check
            return True
        return bool(select.select([fd], [], [], 0.01)[0])

    process_done = False

    while time.time() < min(end_time, end_time_no_output):
        if ready_to_read(fd):
            try:
                data = os.read(fd, 4096)
            except BlockingIOError:
                logger.error("BlockingIOError while reading from subprocess.", exc_info=True)
                break
            if data:
                end_time_no_output = time.time() + no_output_timeout_duration
                buffer += data
                if PROCESS_DONE_MARKER_START in buffer.decode("utf-8", errors="backslashreplace").replace("\r\n", "\n"):
                    process_done = True
                    break
        time.sleep(0.01)  # Prevents CPU hogging

    decoded = buffer.decode("utf-8", errors="backslashreplace").replace("\r\n", "\n")
    body = "\n".join(line for line in decoded.splitlines() if not line.startswith(PROCESS_DONE_MARKER_START))

    if container.poll() is not None:
        msg = f"Subprocess exited unexpectedly.\nCurrent buffer: {decoded}"
        raise RuntimeError(msg, body)

    current_time = time.time()
    if not process_done and current_time >= min(end_time, end_time_no_output):
        if current_time >= end_time:
            msg = f"Timeout reached while reading from subprocess.\nCurrent buffer: {decoded}"
            raise TimeoutError(msg, body)
        else:
            msg = f"No output timeout reached while reading from subprocess.\nCurrent buffer: {decoded}"
            raise NoOutputTimeoutError(msg, body)

    _check_for_too_many_non_unicode_bytes(buffer=buffer)
    _results = PROCESS_DONE_REGEX.search(decoded)
    if _results is None:
        msg = f"Could not find process done marker in last line: {decoded=}, {body=}"
        raise ValueError(msg)
    exit_code = _results.group(1)
    return body.replace(f"{PROCESS_DONE_MARKER_START}{exit_code}{PROCESS_DONE_MARKER_END}", ""), exit_code


def read_session_with_timeout(
    session: subprocess.Popen,
    terminal_pattern: str,
    timeout_duration: int | float,
    no_output_timeout_duration: int | float,
) -> str:
    """
    Read data from a subprocess with a timeout.
    This function uses a file descriptor to read data from the subprocess in a non-blocking way.

    Args:
        session: The session subprocess.
        terminal_pattern: the terminal pattern to indicate end of output.
        timeout_duration: The timeout duration in seconds.

    Returns:
        Output

    Raises:
        TimeoutError: If the timeout duration is reached while reading from the subprocess.
    """
    buffer = b""
    fd = session.stdout.fileno()
    start_time = time.time()
    end_time = start_time + timeout_duration
    end_time_no_output = start_time + no_output_timeout_duration

    # Select is not available on windows
    import select

    def ready_to_read(fd) -> bool:
        return bool(select.select([fd], [], [], 0.01)[0])

    command_done = False
    while time.time() < min(end_time, end_time_no_output) and session.poll() is None:
        if ready_to_read(fd):
            try:
                data = os.read(fd, 4096)
            except BlockingIOError:
                logger.error("BlockingIOError while reading from subprocess.", exc_info=True)
                break
            if data:
                end_time_no_output = time.time() + no_output_timeout_duration
                buffer += data
                if terminal_pattern in buffer.decode("utf-8", errors="backslashreplace").replace("\r\n", "\n"):
                    command_done = True
                    break
        time.sleep(0.01)  # Prevents CPU hogging

    decoded = buffer.decode("utf-8", errors="backslashreplace").replace("\r\n", "\n")
    body = "\n".join(line for line in decoded.splitlines() if not line.startswith(terminal_pattern))

    if session.poll() is not None:
        msg = f"Subprocess exited unexpectedly.\nCurrent buffer: {decoded}"
        raise RuntimeError(msg, body)
    current_time = time.time()
    if not command_done and current_time >= min(end_time, end_time_no_output):
        if current_time >= end_time:
            msg = f"Timeout reached while reading from subprocess.\nCurrent buffer: {decoded}"
            raise TimeoutError(msg, body)
        else:
            msg = f"No output timeout reached while reading from subprocess.\nCurrent buffer: {decoded}"
            raise NoOutputTimeoutError(msg, body)

    return body


def get_background_pids(container_obj: Container):
    pids = container_obj.exec_run("ps -eo pid,comm --no-headers").output.decode().split("\n")
    pids = [x.split() for x in pids if x]
    pids = [x for x in pids if x[1] not in {"ps"} and x[0] != "1"]
    bash_pids = [x for x in pids if x[1] == "bash"]
    other_pids = [x for x in pids if x[1] not in {"bash"}]
    return bash_pids, other_pids


def terminate_docker_compose(docker_compose_path: Path) -> None:
    terminate_cmd = [
        "docker",
        "compose",
        "-f",
        str(docker_compose_path),
        "down",
    ]
    logger.debug("Terminating docker-compose with command: %s", shlex.join(terminate_cmd))
    compose = subprocess.Popen(
        terminate_cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        bufsize=1,  # line buffered
    )
    _, error = compose.communicate(timeout=DOCKER_COMPOSE_TERMINATION_DELAY)
    if error:
        logger.error(f"Unexpected compose termination error: {error}")


def attach_network_interface_to_container(container_name: str) -> None:
    cmd = [
        "docker",
        "network",
        "connect",
        "ctfnet",
        container_name,
    ]
    logger.debug("Attaching NIC to container with command: %s", shlex.join(cmd))
    compose = subprocess.Popen(
        cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        bufsize=1,  # line buffered
    )
    _, error = compose.communicate(timeout=DOCKER_START_UP_DELAY)
    if error:
        logger.error(f"Unexpected compose setup error: {error}")
        raise RuntimeError(error)


def get_docker_compose(docker_compose_path: Path) -> Path:
    startup_cmd = [
        "docker",
        "compose",
        "-f",
        str(docker_compose_path),
        "up",
        "-d",
        "--force-recreate",
    ]
    logger.debug("Starting docker-compose with command: %s", shlex.join(startup_cmd))
    compose = subprocess.Popen(
        startup_cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        bufsize=1,  # line buffered
    )
    _, error = compose.communicate(timeout=DOCKER_COMPOSE_STARTUP_DELAY)
    if error:
        logger.error(f"Unexpected compose setup error: {error}")
    return docker_compose_path


def _get_container_mounts_list(container_mounts: list[str]) -> list[docker.types.Mount]:
    try:
        for i in range(len(container_mounts)):
            path = Path(container_mounts[i]).absolute()
            if path.is_dir():
                container_mounts[i] = docker.types.Mount(source=str(path), target=f"/{path.name}")
        return container_mounts
    except Exception:
        logger.warning("Failed to process container mounts, skipping mount.")
        return []


def _get_non_persistent_container(
    ctr_name: str, image_name: str, container_mounts: list[str]
) -> tuple[subprocess.Popen, set[str]]:
    startup_cmd = [
        "docker",
        "run",
        "-i",
        "--rm",
        *[item for mount in container_mounts for item in ("-v", f"{Path(mount).absolute()}:/{Path(mount).name}")],
        "--name",
        ctr_name,
        image_name,
        "/bin/bash",
        "-l",
    ]
    logger.debug("Starting container with command: %s", shlex.join(startup_cmd))
    container = subprocess.Popen(
        startup_cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        bufsize=1,  # line buffered
    )
    time.sleep(DOCKER_START_UP_DELAY)
    # try to read output from container setup (usually an error), timeout if no output
    output = read_with_timeout(container, lambda: list(), timeout_duration=2)
    if output:
        logger.error(f"Unexpected container setup output: {output}")
    # bash PID is always 1 for non-persistent containers
    return container, {
        "1",
    }


def _get_persistent_container(
    ctr_name: str, image_name: str, container_mounts: list[str], persistent: bool = False
) -> tuple[subprocess.Popen, set[str]]:
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
            msg = f"Unexpected container status: {container_obj.status}"
            raise RuntimeError(msg)
    else:
        container_mounts = _get_container_mounts_list(container_mounts)
        container_obj = client.containers.run(
            image_name,
            command="/bin/bash -l -m",
            name=ctr_name,
            stdin_open=True,
            tty=True,
            detach=True,
            auto_remove=not persistent,
            mounts=container_mounts,
        )
        container_obj.start()
    startup_cmd = [
        "docker",
        "exec",
        "-i",
        ctr_name,
        "/bin/bash",
        "-l",
    ]
    logger.debug("Starting container with command: %s", shlex.join(startup_cmd))
    container = subprocess.Popen(
        startup_cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
        bufsize=1,  # line buffered
    )
    time.sleep(DOCKER_START_UP_DELAY)
    # try to read output from container setup (usually an error), timeout if no output
    output = read_with_timeout(container, lambda: list(), timeout_duration=2)
    if output:
        logger.error(f"Unexpected container setup output: {output}")
    # Get the process IDs of the container
    # There should be at least a head process and possibly one child bash process
    bash_pids, other_pids = get_background_pids(container_obj)
    total_time_slept = DOCKER_START_UP_DELAY
    # Let's wait for a maximum of 5 x DOCKER_START_UP_DELAY seconds
    # and then check again.
    while len(bash_pids) > 1 or len(other_pids) > 0:
        time.sleep(1)
        total_time_slept += 1
        bash_pids, other_pids = get_background_pids(container_obj)
        if total_time_slept > 5 * DOCKER_START_UP_DELAY:
            break
    bash_pid = 1
    if len(bash_pids) == 1:
        bash_pid = bash_pids[0][0]
    elif len(bash_pids) > 1 or len(other_pids) > 0:
        msg = (
            "Detected alien processes attached or running. Please ensure that no other agents "
            f"are running on this container. PIDs: {bash_pids}, {other_pids}"
        )
        raise RuntimeError(msg)
    return container, {str(bash_pid), "1"}


def get_container(
    ctr_name: str, image_name: str, container_mounts: list[str], persistent: bool = False
) -> tuple[subprocess.Popen, set]:
    """
    Get a container object for a given container name and image name

    Arguments:
        ctr_name (str): Name of container
        image_name (str): Name of image
        persistent (bool): Whether to use a persistent container or not
    Returns:
        Container object
    """
    if not image_exists(image_name):
        msg = (
            f"Image {image_name} not found. Please ensure it is built and available. "
            "Please double-check that you followed all installation/setup instructions from the "
            "readme."
        )
        raise RuntimeError(msg)

    if persistent:
        return _get_persistent_container(ctr_name, image_name, container_mounts=container_mounts)
    else:
        return _get_non_persistent_container(ctr_name, image_name, container_mounts=container_mounts)


def image_exists(image_name: str) -> bool:
    """
    Check that the image exists and give some better error messages.

    Arguments:
        image_name: Name of image
    Returns:
        bool: True if image exists
    """
    try:
        client = docker.from_env()
    except docker.errors.DockerException as e:
        docker_not_running = any(
            (
                "connection aborted" in str(e).lower(),
                "connection refused" in str(e).lower(),
                "error while fetching server api version" in str(e).lower(),
            ),
        )
        if docker_not_running:
            msg = (
                "Probably the Docker daemon is not running. Please start the Docker daemon and try again. "
                "If Docker issues persist, please check out https://princeton-nlp.github.io/SWE-agent/installation/tips/"
            )
            raise RuntimeError(msg) from e
        raise
    filterred_images = client.images.list(filters={"reference": image_name})
    if len(filterred_images) == 0:
        return False
    elif len(filterred_images) > 1:
        RuntimeError(f"Multiple images found for {image_name}, that's weird.")
    attrs = filterred_images[0].attrs
    if attrs is not None:
        logger.info(
            f"Found image {image_name} with tags: {attrs['RepoTags']}, created: {attrs['Created']} "
            f"for {attrs['Os']} {attrs['Architecture']}.",
        )
    return True


def get_commit(api: GhApi, owner: str, repo: str, ref: str | None = None):
    """Get commit object from github api

    Args:
        api (GhApi):
        owner (str): Repo owner, e.g., "princeton-nlp"
        repo (str): Repo, e.g., "SWE-agent"
        ref (str, optional): Branch, tag or commit hash

    Returns:
        _type_: _description_
    """
    if ref:
        return api.repos.get_commit(owner, repo, ref)
    return api.repos.list_commits(owner, repo)[0]


class InvalidGithubURL(ValueError): ...


def parse_gh_issue_url(issue_url: str) -> tuple[str, str, str]:
    """
    Returns:
        owner: Repo owner
        repo: Repo name
        issue number: Issue number as str

    Raises:
        InvalidGithubURL: If the URL is not a valid github issue URL
    """
    match = GITHUB_ISSUE_URL_PATTERN.search(issue_url)
    if not match:
        msg = f"Invalid GitHub issue URL: {issue_url}"
        raise InvalidGithubURL(msg)
    res = match.groups()
    assert len(res) == 3
    return tuple(res)  # type: ignore


def parse_gh_repo_url(repo_url: str) -> tuple[str, str]:
    """
    Returns:
        owner: Repo owner/org
        repo: Repo name

    Raises:
        InvalidGithubURL: If the URL is not a valid github repo URL
    """
    match = GITHUB_REPO_URL_PATTERN.search(repo_url)
    if not match:
        msg = f"Invalid GitHub issue URL: {repo_url}"
        raise InvalidGithubURL(msg)
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


def get_problem_statement_from_github_issue(owner: str, repo: str, issue_number: str, *, token: str | None = "") -> str:
    """Return problem statement from github issue"""
    api = GhApi(token=token)
    issue = api.issues.get(owner, repo, issue_number)
    title = issue.title if issue.title else ""
    body = issue.body if issue.body else ""
    return f"{title}\n{body}\n"


class InstanceBuilder:
    def __init__(self, token: str | None = None):
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
        self.args["problem_statement"] = get_problem_statement_from_github_issue(
            owner,
            repo,
            issue_number,
            token=self.token,
        )
        self.args["instance_id"] = f"{owner}__{repo}-i{issue_number}"
        self.args["problem_statement_source"] = "online"

    def set_server_description(self, server_name: str | None, port: int | None) -> None:
        """For CTF challenges"""
        if server_name is None or port is None:
            self.args["challenge"]["server_description"] = ""
            return
        if self.args["challenge"]["category"] in {"web", "misc"} and self.args["challenge"].get("proto") != "nc":
            self.args["challenge"]["server_description"] = (
                f"The challenge web server is running on `{server_name}` port `{port}` and you can access it from within the container environment using `curl http://{server_name}:{port}`."
            )
        else:
            self.args["challenge"]["server_description"] = (
                f"The challenge web server is running on `{server_name}` port `{port}` and you can access it from within the container environment using `connect_start {server_name} {port}`."
            )

    def set_problem_statement_from_challenge_json(self, file_path: str) -> None:
        """For CTF challenges"""
        challenge = json.loads(Path(file_path).read_text())
        self.args["challenge"] = challenge
        self.args["challenge"]["files"] = challenge.get("files", [])
        self.args["challenge"]["points"] = challenge.get("points", 10)
        self.args["challenge"]["category_friendly"] = CTF_CHALLENGES_CATEGORIES.get(challenge["category"])
        if (Path(file_path).parent / "docker-compose.yml").is_file():
            logger.debug(f"Found docker_compose file in {Path(file_path).parent}")
            self.args["challenge"]["docker_compose"] = Path(file_path).parent / "docker-compose.yml"
        self.args["challenge"]["port"] = challenge.get("internal_port") or challenge.get("port")
        if "box" in challenge:
            self.args["challenge"]["server_name"] = challenge["box"] or "127.0.0.1"
        else:
            self.args["challenge"]["server_name"] = ""
        self.args["challenge"]["file_path"] = file_path
        self.set_server_description(self.args["challenge"]["server_name"], self.args["challenge"]["port"])
        self.set_problem_statement_from_text(f"{challenge['name']} {challenge['description']}")
        self.args["instance_id"] = (
            # sanitize 'name' to only alphanumeric characters
            challenge.get("category", "misc") + "_" + "".join(a for a in self.args["challenge"]["name"] if a.isalnum())
        )

    def set_problem_statement_from_file(self, file_path: str):
        if Path(file_path).name == "challenge.json":
            self.set_problem_statement_from_challenge_json(file_path)
        else:
            self.set_problem_statement_from_text(Path(file_path).read_text())

    def set_problem_statement_from_text(self, text: str):
        self.args["problem_statement"] = text
        self.args["instance_id"] = hashlib.sha256(self.args["problem_statement"].encode()).hexdigest()[:6]
        self.args["problem_statement_source"] = "local"

    def set_problem_statement(self, data_path: str):
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

    def set_repo_info_from_gh_url(self, url: str, base_commit: str | None = None):
        owner, repo = parse_gh_repo_url(url)
        self.args["repo"] = f"{owner}/{repo}"
        self.args["repo_type"] = "github"
        # Always get commit hash, because base_commit can also be branch or tag
        api = GhApi(token=self.token)
        self.args["base_commit"] = get_commit(api, owner, repo, ref=base_commit).sha
        if base_commit != self.args["base_commit"]:
            logger.info(f"Base commit reference {base_commit} resolved to commit hash {self.args['base_commit']}")
        self.args["version"] = self.args["base_commit"][:7]

    def set_repo_info_from_local_path(self, path: str, base_commit: str | None = None):
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
            if repo.is_dirty() and "PYTEST_CURRENT_TEST" not in os.environ:
                msg = f"Local git repository {path} is dirty. Please commit or stash changes."
                raise ValueError(msg)
            self.args["base_commit"] = repo.head.object.hexsha
        self.args["version"] = self.args["base_commit"][:7]

    def set_repo_info(self, repo: str, base_commit: str | None = None):
        if is_github_repo_url(repo):
            self.set_repo_info_from_gh_url(repo, base_commit=base_commit)
        elif Path(repo).is_dir():
            self.set_repo_info_from_local_path(repo, base_commit=base_commit)
        else:
            msg = f"Could not determine repo path from {repo=}."
            raise ValueError(msg)

    def set_from_dict(self, instance_dict: dict[str, Any]):
        self.args |= instance_dict

    def set_missing_fields(self):
        # TODO: This field is only needed while swe_env is using some questionable logic
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
            msg = f"Missing required fields: {missing=}"
            raise ValueError(msg)
        if self.args["repo_type"] not in {"github", "local"}:
            msg = f"Invalid repo type: {self.args['repo_type']=}"
            raise ValueError(msg)
        if self.args["repo_type"] == "github" and self.args["repo"].count("/") != 1:
            msg = f"Invalid repo format for {self.args['repo_type']=}: {self.args['repo']=}"
            raise ValueError(msg)

    def build(self) -> dict[str, Any]:
        self.set_missing_fields()
        self.validate()
        return self.args


def get_instances(
    file_path: str,
    base_commit: str | None = None,
    split: str | None = None,
    token: str | None = None,
    *,
    repo_path: str = "",
) -> list[dict[str, Any]]:
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

    # The next if statement is very brittle logic to determine if we're processing a single instance
    if (
        file_path.startswith("text://")
        or (
            Path(file_path).is_file()
            and (Path(file_path).suffix in [".md", ".txt"] or Path(file_path).name == "challenge.json")
        )
        or is_github_issue_url(file_path)
    ):
        ib = InstanceBuilder(token=token)
        ib.set_problem_statement(file_path)
        if repo_path:
            ib.set_repo_info(repo_path, base_commit=base_commit)
        elif is_github_repo_url(file_path):
            ib.set_repo_info_from_gh_url(file_path, base_commit=base_commit)
        else:
            msg = f"Could not determine repo path from {file_path=}, {repo_path=}"
            raise ValueError(msg)

        return [ib.build()]

    if base_commit:
        msg = "base_commit must be empty if running over multiple problem statements"
        raise ValueError(msg)

    if repo_path:
        if not Path(repo_path).exists():
            msg = f"Specified repository path {repo_path} does not exist"
            raise FileNotFoundError(msg)
        msg = "repo_path must be empty if running over multiple problem statements"
        raise ValueError(msg)

    # If file_path is a directory, attempt load from disk
    if Path(file_path).is_dir():
        try:
            dataset_or_dict = load_from_disk(file_path)
            if isinstance(dataset_or_dict, dict):
                return postproc_instance_list(dataset_or_dict[split])
            return postproc_instance_list(dataset_or_dict)
        except FileNotFoundError:
            # Raised by load_from_disk if the directory is not a dataset directory
            pass

    if base_commit is not None:
        msg = "base_commit must be None if data_path is not a github issue url"
        raise ValueError(msg)

    # If file_path is a file, load the file
    if file_path.endswith(".json"):
        with open(file_path) as file:
            return postproc_instance_list(json.load(file))
    if file_path.endswith(".jsonl"):
        return postproc_instance_list([json.loads(x) for x in Path(file_path).read_text().splitlines(keepends=True)])

    # Attempt load from HF datasets as a last resort
    try:
        return postproc_instance_list(load_dataset(file_path, split=split))
    except Exception as e:
        msg = (
            f"Could not load instances from {file_path}. "
            "Please ensure --data_path is a GitHub URL, a SWE-bench HuggingFace dataset, or a JSON/JSONL file."
        )
        raise ValueError(msg) from e


def get_associated_commit_urls(org: str, repo: str, issue_number: str, *, token: str = "") -> list[str]:
    """Return the URLs of commits that would close an issue."""
    api = GhApi(token=token)
    # Strangely the "pull_request" field of api.issues.get is often not set
    # so we have to go through the events to check if there's a commit
    events = api.issues.list_events(org, repo, issue_number)
    commit_urls = []
    for event in events:
        if event.event != "referenced":
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


def format_trajectory_markdown(trajectory: list[dict[str, str]]):
    """Format a trajectory as a markdown string for use in gh PR description."""
    prefix = [
        "<details>",
        "<summary>Thought process ('trajectory') of SWE-agent (click to expand)</summary>",
        "",
        "",
    ]
    steps = []
    for i, step in enumerate(trajectory):
        step_strs = [
            f"**🧑‍🚒 Response ({i})**: ",
            f"{step['response'].strip()}",
            f"**👀‍ Observation ({i})**:",
            "```",
            f"{remove_triple_backticks(step['observation']).strip()}",
            "```",
        ]
        steps.append("\n".join(step_strs))
    suffix = [
        "",
        "</details>",
    ]
    return "\n".join(prefix) + "\n\n---\n\n".join(steps) + "\n".join(suffix)


class PatchFormatter:
    def __init__(
        self,
        patch: str,
        read_method: Callable[[str], str],
    ):
        """Given the final patch and access to the container that contains the repository,
        extract relevant lines from the modified file.

        Args:
            patch: The patch as a string.
            read_method: Callable with path to file (relative to repository root) as argument
                that returns the file content as a string.
        """
        self._patch = PatchSet(patch)
        self._patched_files: dict[str, str] = {}
        self._original_files: dict[str, str] = {}
        self._patch_applied = True
        self._read_file = read_method
        self._read_files(original=False)

    @staticmethod
    def _merge_intervals(starts: list[int], stops: list[int]) -> tuple[list[int], list[int]]:
        """Given two lists of integers, starts and stops, merges all overlapping intervals.

        For example `starts=[1, 5, 18]`, `stops=[10, 13, 20]`
        should return `starts=[1, 18]`, `stops=[13, 20]`
        """

        intervals = sorted(zip(starts, stops))
        merged = []
        for start, stop in intervals:
            if not merged or merged[-1][1] < start:
                # No overlap
                merged.append([start, stop])
            else:
                # Overlap
                merged[-1][1] = max(merged[-1][1], stop)
        # Unzip again
        merged_starts, merged_stops = zip(*merged)
        return list(merged_starts), list(merged_stops)

    def format_file(self, text: str, starts: list[int], stops: list[int], *, linenos: bool = True) -> str:
        """Reads file and returns string representation of the relevant lines.

        Args:
            path: The path to the file within the repo location
            starts: The starting line numbers of the relevant lines. The first line is line 1.
            stops: The stopping line numbers of the relevant lines. The stop is not inclusive.
                The first line is line 1.
            linenos: Whether to include line numbers
        """
        assert len(starts) == len(stops)
        assert all(start >= 1 for start in starts)
        assert all(start < stop for start, stop in zip(starts, stops))
        starts, stops = self._merge_intervals(starts, stops)
        assert all(hunk1_start < hunk2_start for hunk1_start, hunk2_start in zip(starts, starts[1:]))
        out: list[str] = []
        if starts[0] > 1:
            # Count from 1
            out.append(f"[{starts[0]-1} lines above omitted]")
        last_stop: int | None = None
        lines = text.splitlines()
        for start, stop in zip(starts, stops):
            assert start >= 1
            if last_stop is not None:
                n_omitted = start - last_stop
                # Check that we have non-overlapping hunks
                assert n_omitted >= 0
                if n_omitted:
                    out.append(f"\n[{n_omitted} lines omitted]\n")
            # Count from 1
            these_lines = lines[start - 1 : stop - 1]
            if linenos:
                out.append("\n".join([f"{i:6d}: {l}" for i, l in enumerate(these_lines, start=start)]))
            else:
                out.append("\n".join(these_lines))
            last_stop = stop
        if last_stop < len(lines):
            # Stop is not inclusive
            omitted = len(lines) - last_stop
            assert omitted > 0
            out.append(f"[{omitted} lines below omitted]")
        return "\n".join(out)

    def _get_hunk_lines(self, original: bool, *, context_length: int) -> dict[str, tuple[list[int], list[int]]]:
        """Get the starts and stops for all files in the patch.

        Args:
            original: Whether to read the original file or the patched file
            context_length: The number of lines to include above and below the hunk

        Returns:
            A dictionary with the file path as key and a tuple of lists of starts and stops as value.
        """
        out: dict[str, tuple[list[int], list[int]]] = {}
        for patch in self._patch:
            if not patch.is_modified_file:
                continue
            starts: list[int] = []
            stops: list[int] = []
            for hunk in patch:
                if original:
                    # 1 is the lowest line number
                    start = max(1, hunk.source_start - context_length)
                    stop = hunk.source_start + hunk.source_length + context_length
                else:
                    start = max(1, hunk.target_start - context_length)
                    stop = hunk.target_start + hunk.target_length + context_length
                starts.append(start)
                stops.append(stop)
            out[patch.path] = (starts, stops)
        return out

    def _read_files(self, original: bool) -> None:
        for patch in self._patch:
            path = patch.path
            if not patch.is_modified_file:
                continue
            if original:
                msg = "Original file reading not implemented"
                raise NotImplementedError(msg)
            else:
                assert self._patch_applied
                self._patched_files[path] = self._read_file(path)

    @staticmethod
    def concat_files_strings(files: dict[str, str]) -> str:
        """Concatenate multiple `read_files` outputs into a single string."""
        out = []
        for path, content in files.items():
            out.append(f"[File: {path}]\n{content}")
        return "\n\n".join(out)

    def get_files_str(self, *, original: bool, context_length: int | None = 50, linenos: bool = True) -> str:
        hunk_lines = self._get_hunk_lines(original=original, context_length=context_length)
        sources = self._original_files if original else self._patched_files
        return self.concat_files_strings(
            {path: self.format_file(text, *hunk_lines[path], linenos=linenos) for path, text in sources.items()}
        )


def extract_flag_format(flag: str) -> str:
    flag_format = re.sub(r"{.*}$", "{...}", flag)
    return flag_format if flag_format != flag else "..."
