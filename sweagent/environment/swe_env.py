from __future__ import annotations

import datetime
import hashlib
import logging
import os
import random
import re
import subprocess
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import gymnasium as gym
import yaml
from ghapi.all import GhApi
from git import Repo
from rich.logging import RichHandler
from simple_parsing.helpers.serialization.serializable import FrozenSerializable
from swebench import MAP_VERSION_TO_INSTALL, get_environment_yml, get_requirements

import docker
from sweagent.environment.utils import (
    LOGGER_NAME,
    PROCESS_DONE_MARKER_END,
    PROCESS_DONE_MARKER_START,
    InvalidGithubURL,
    copy_anything_to_container,
    copy_file_to_container,
    format_trajectory_markdown,
    get_container,
    get_gh_issue_data,
    get_instances,
    image_exists,
    parse_gh_issue_url,
    read_with_timeout,
    read_with_timeout_experimental,
)
from sweagent.utils.config import Config

LONG_TIMEOUT = 500
PATH_TO_REQS = "/root/requirements.txt"
PATH_TO_ENV_YML = "/root/environment.yml"

handler = RichHandler(show_time=False, show_path=False)
handler.setLevel(logging.DEBUG)
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = False


@dataclass(frozen=True)
class EnvironmentArguments(FrozenSerializable):
    """Configure data sources and setup instructions for the environment in which we solve the tasks."""

    # Source of issue statement/problem statement. To run over a batch of issues: Path to a data file
    # (`json`, `jsonl`) or directory. To run over single issue: github issue url or path to markdown file
    # with problem statement or problem statement as text prefixed with `text://`.
    data_path: str
    image_name: str
    split: str = "dev"
    # Specify a branch name or a commit hash to checkout before running the task.
    # Only used when running over a single problem statement/issue.
    base_commit: str | None = None
    container_name: str | None = None
    install_environment: bool = True
    timeout: int = 35
    verbose: bool = False
    no_mirror: bool = False
    cache_task_images: bool = False
    # Custom environment setup. Currently only used when data_path points to a single issue.
    # This needs to be either a string pointing to a yaml file (with yaml, yml file extension)
    # or a shell script (with sh extension).
    # See https://github.com/princeton-nlp/SWE-agent/pull/153 for more information
    environment_setup: str | None = None
    # Only used when running on single issue. Path to local repository or github repository.
    repo_path: str = ""


class EnvHook:
    def on_init(self): ...

    def on_copy_repo_started(self, *, repo_type: str, repo_path: str): ...

    def on_install_env_started(self): ...

    def on_close(self): ...


class SWEEnv(gym.Env):
    """Gym environment for SWE-bench. This class should handle all communication with the docker container."""

    name = "swe_main"
    cached_image_prefix = "swe-agent-task-env-"

    def __init__(self, args: EnvironmentArguments):
        super().__init__()
        self.args = args
        self.base_commit = None
        self.communicate_output = None
        self.container_name = args.container_name
        self.install_environment = args.install_environment
        self.logger = logger
        self.persistent = args.container_name is not None
        self.returncode = None
        if not self.args.verbose:
            self.logger.disabled = True

        #: The commit hash of the swe-agent repository
        self.commit_sha = None
        try:
            repo = Repo(search_parent_directories=True)
            self.commit_sha = repo.head.object.hexsha
        except KeyboardInterrupt:
            raise
        except:
            logger.warning("Failed to get commit hash for this repo")

        self._github_token: str = Config().get("GITHUB_TOKEN", "")  # type: ignore

        # Load Task Instances
        self.data_path = self.args.data_path
        self.data = get_instances(
            self.data_path,
            self.args.base_commit,
            self.args.split,
            token=self._github_token,
            repo_path=self.args.repo_path,
        )
        #: Instance we're currently processing. Gets set in self.reset.
        self.record = None
        self.logger.info(f"💽 Loaded dataset from {self.data_path}")

        # Establish connection with execution container
        self.image_name = args.image_name
        self._reset_container()

        # Set timeout
        self.timeout = self.args.timeout
        self.idx = 0
        self.clean_multi_line_functions = lambda x: x
        self.hooks = []

    def _get_cached_task_image_name(self) -> str:
        assert self.record is not None
        inputs: list[str] = [
            self.record["repo"],
            self.record["base_commit"],
            self.args.environment_setup or "no_setup",
        ]
        tag = hashlib.sha256("".join(inputs).encode()).hexdigest()[:50]
        return f"{self.cached_image_prefix}{tag}"

    def add_hook(self, hook: EnvHook):
        hook.on_init()
        self.hooks.append(hook)

    @property
    def _repo_name(self) -> str:
        """Name of the local copy of the repository"""
        assert self.record is not None
        return self.record["repo"].replace("/", "__")

    def _copy_repo(self) -> str:
        """Clone/copy repository/codebase in container
        Returns:
            folder name of clone
        """
        assert self.record is not None  # mypy
        for hook in self.hooks:
            hook.on_copy_repo_started(repo_type=self.record["repo_type"], repo_path=self.record["repo"])
        if self.record["repo_type"] == "local":
            copy_anything_to_container(
                self.container_obj, self.record["repo"].removeprefix("local://"), "/" + self._repo_name
            )
            self.communicate_with_handling(
                input=f"chown -R root:root {self._repo_name}",
                error_msg="Failed to change permissions on copied repository",
            )
            return self._repo_name
        assert self.record["repo_type"] == "github"
        token_prefix = ""
        if self._github_token:
            token_prefix = f"{self._github_token}@"
        # fixme: This if statement is brittle and should probably be replaced with better logic
        if not self.args.no_mirror and self.record["problem_statement_source"] == "swe-bench":
            self.logger.info(f"{self._repo_name} not found in container, cloning...")
            self.communicate_with_handling(
                input=f"git clone https://{token_prefix}github.com/swe-bench/{self._repo_name}.git",
                error_msg="Failed to clone repository from mirror",
                timeout_duration=LONG_TIMEOUT,
            )
            return self._repo_name
        else:
            logger.info("Trying to clone from non-mirror...")
            self.communicate_with_handling(
                input=f"git clone https://{token_prefix}github.com/{self.record['repo']}.git {self._repo_name}",
                error_msg="Failed to clone repository from non-mirror",
                timeout_duration=LONG_TIMEOUT,
            )
            return self._repo_name

    def reset(self, index: int | None = None, apply_test_patch: bool = False) -> tuple[str | None, dict]:
        """
        Function to reset container between each task instance.
        * Clones instance's repository
        * Cleans repository of prior modifications
        * Resets environment variables
        * Check out base commit

        Arguments:
            index (`int`) - index of task instance to reset to
        Returns:
            observation (`str`) - output from container
            info (`dict`) - additional information (e.g. debugging information)
        """
        info = {}
        info["commit_sha"] = self.commit_sha

        # Get task instance
        self.idx = index if index is not None else self.idx
        self.record = self.data[self.idx]
        self.idx += 1

        # Set query, gold command
        self.base_commit = self.record["base_commit"]
        self.query = self.record["problem_statement"]
        self.reward = None

        ### Reset Container ###

        if self.args.cache_task_images:
            cached_image = self._get_cached_task_image_name()
            if image_exists(cached_image):
                logger.info(f"Restore environment from cached image {cached_image}")
                self.close()  # stop current container
                self._init_container(cached_image=cached_image)
                self.communicate("export $(xargs </.env)")
                envs = self.communicate("env")
                logger.debug(f"Environment variables restored from the image:\n{envs}\n")
                if apply_test_patch:
                    self._apply_test_patch()
                return None, info
            else:
                logger.info(f"Cached image {cached_image} not found, rebuilding task environment...")

        # Clone repository if not already cloned
        self.communicate(input="cd /")
        folders = self.communicate(input="ls").split("\n")
        if self._repo_name not in folders:
            self._copy_repo()

        # Clean repository of any modifications + Checkout base commit
        for cmd in [
            "echo -n > /root/files_to_edit.txt",
            f"cd {self._repo_name}",
            "export ROOT=$(pwd -P)",
            "git status",
            "git restore .",
            f"git reset --hard {self.base_commit}",
            "git clean -fdxq",
        ]:
            self.communicate_with_handling(
                input=cmd,
                error_msg="Failed to clean repository",
            )

        # Reset environment variables
        for cmd in [
            'export CURRENT_FILE=""',
            "export CURRENT_LINE=0",
            "export SEARCH_RESULTS=()",
            "export SEARCH_FILES=()",
            "export SEARCH_INDEX=0",
        ]:
            self.communicate_with_handling(
                input=cmd,
                error_msg="Failed to reset environment variables",
            )

        # Set up environment
        self.communicate_with_handling(
            "source /root/miniconda3/etc/profile.d/conda.sh",
            error_msg="Failed to source conda",
        )

        system = self.communicate("uname -s").strip().lower()
        arch = self.communicate("uname -m").strip().lower()
        if system == "linux" and arch == "x86_64":
            self.communicate_with_handling(
                "apt update; apt install build-essential -y",
                error_msg="Failed to install build-essential",
                timeout_duration=LONG_TIMEOUT,
            )

        # Call install environment helper function if specified
        if self.install_environment:
            self.install_env()
        # Install mypy for linting purposes
        self.communicate_with_handling("pip install flake8", error_msg="Failed to install flake8 (lint library)")

        if self.args.cache_task_images:
            envs = self.communicate("env")
            logger.debug(f"Environment variables to save:\n{envs}\n")
            self.communicate("env >> /.env")
            assert self.container_obj is not None  # mypy
            self.container_obj.commit(cached_image)
            logger.info(f"Container with environment {self.container_obj.id} cached as image {cached_image}")

        if apply_test_patch:
            self._apply_test_patch()
        # Write any metadata to info if necessary
        return None, info

    def _apply_test_patch(self):
        """
        Apply test patch for oracle setting
        """
        assert self.record is not None
        path_to_patch = "test.patch"
        with open(path_to_patch, "w") as f:
            f.write(self.record["test_patch"])
        subprocess.run(
            f"docker cp {path_to_patch} {self.container_name}:/root/test.patch",
            shell=True,
        )
        self.communicate_with_handling(
            input="git apply /root/test.patch", error_msg="Failed to apply test patch correctly"
        )
        os.remove(path_to_patch)

    def step(self, action: str) -> tuple[str | None, int, bool, dict]:
        """
        Runs given action in environment and returns corresponding output

        Args:
            action (`str`) - command to run in bash shell

        Returns:
            observation (`str`) - output from container
            reward (`float`) - value between 0 and 1 quantifying correctness of output + environment state
            done (`bool`) - whether task is over
            info (`dict`) - additional information (e.g. debugging information)
        """
        info = {}

        observation = ""
        # Handle special actions
        if action.strip() == "skip":
            observation = "Skipped"
            info["exit_status"] = "skipped"
            return observation, 0, True, info
        if action in {"exit_context", "exit_cost", "exit_error", "exit_format", "exit_api"}:
            try:
                observation = self.communicate(input="submit")
                submission = self.get_submission(observation)
                assert submission is not None and submission.strip() != "", AssertionError("No submission found.")
                self.logger.info(f"Found submission: {submission}")
                info["exit_status"] = f"submitted ({action})"
                info["submission"] = submission
                observation = "Exited (autosubmitted)"
                logger.info("Exiting with autosubmission")
                return observation, 0, True, info
            except KeyboardInterrupt:
                raise
            except:
                observation = "Exited"
                info["exit_status"] = action
                return observation, 0, True, info

        # Attempt to run action in container
        observation = ""
        try:
            observation = self.communicate(input=action, timeout_duration=25)
        except TimeoutError:
            try:
                self.interrupt()
                observation += "\nEXECUTION TIMED OUT"
            except RuntimeError as e:
                observation += "\nEXECUTION TIMED OUT AND INTERRUPT FAILED. RESTARTING PROCESS."
                info["exit_status"] = "early_exit"
                logger.warning(f"Failed to interrupt container: {e}\nRESTARTING PROCESS.")
                self.reset_container()
                return observation, 0, True, info
        except RuntimeError as e:
            observation += "\nCOMMAND FAILED TO EXECUTE. RESTARTING PROCESS."
            info["exit_status"] = "early_exit"
            logger.warning(f"Failed to execute command: {e}\nRESTARTING PROCESS.")
            self.reset_container()
            return observation, 0, True, info
        except BrokenPipeError as e:
            observation += "\nBROKEN PIPE ERROR. RESTARTING PROCESS."
            info["exit_status"] = "early_exit"
            logger.error(f"Broken pipe error: {e}\nRESTARTING PROCESS.")
            self.reset_container()
            return observation, 0, True, info
        except Exception:
            observation += "\nEXECUTION FAILED OR COMMAND MALFORMED"

        # Record submission and end episode if `submit` keyword found
        submission = self.get_submission(observation)
        if submission is not None:
            self.logger.info(f"Found submission: {submission}")
            info["exit_status"] = "submitted"
            info["submission"] = submission if submission.strip() != "" else None
            observation = submission if submission.strip() != "" else None
            return observation, 0, True, info
        return observation, 0, False, info

    def close(self):
        """
        Handle environment shutdown
        """
        self.logger.info("Beginning environment shutdown...")
        try:
            self.communicate(input="exit")
        except KeyboardInterrupt:
            raise
        except:
            pass
        assert self.container is not None
        assert self.container_obj is not None
        self.container.terminate()
        if self.persistent:
            if self.container_obj.status not in {"paused", "exited"}:
                self.container_obj.pause()
                self.logger.info("Agent container paused")
            else:
                self.logger.info(f"Agent container status: {self.container_obj.status}")
        else:
            try:
                self.container_obj.remove(force=True)
            except KeyboardInterrupt:
                raise
            except:
                pass
            self.logger.info("Agent container stopped")
        for hook in self.hooks:
            hook.on_close()

    # MARK: Helper functions #

    def _reset_container(self) -> None:
        if hasattr(self, "container"):
            try:
                self.container.terminate()
            except KeyboardInterrupt:
                raise
            except:
                pass
        self._init_container()
        self._init_scripts()

    def reset_container(self) -> None:
        self.close()
        self.container = None
        self.container_obj = None
        self._reset_container()

    def _init_container(self, cached_image: str | None = None) -> None:
        """
        Handles container initialization. Defines container name and creates it.
        If cached_image is provided, it will use that image name instead of the default.
        """
        image_name = self.image_name
        if cached_image is not None:
            image_name = cached_image
            logger.info(f"Using cached image: {image_name}")
        if self.container_name is None:
            process_id = str(os.getpid())
            current_time = str(datetime.datetime.now())
            unique_string = current_time + process_id
            hash_object = hashlib.sha256(unique_string.encode())
            # Cannot have colons/slashes in container name, but those are important in image names
            # i.e., when we want swe-agent to pull the image from dockerhub
            image_name_sanitized = image_name.replace("/", "-")
            image_name_sanitized = image_name_sanitized.replace(":", "-")
            self.container_name = f"{image_name_sanitized}-{hash_object.hexdigest()[:10]}"
        self.container, self.parent_pids = get_container(self.container_name, image_name, persistent=self.persistent)
        try:
            client = docker.from_env(timeout=600)
        except docker.errors.DockerException as e:
            if "Error while fetching server API version" in str(e):
                msg = "Docker is not running. Please start Docker and try again."
                raise RuntimeError(msg) from e
        try:
            self.container_obj = client.containers.get(self.container_name)
        except docker.errors.NotFound:
            logger.debug("Couldn't find container. Let's wait and retry.")
            time.sleep(3)
            self.container_obj = client.containers.get(self.container_name)
        self.logger.info("🌱 Environment Initialized")

    def _init_scripts(self):
        """
        Initialize custom commands within container
        """
        self.communicate_with_handling(
            "source /root/.bashrc",
            error_msg="Failed to source .bashrc",
        )
        self.communicate_with_handling(
            "mkdir -p /root/commands",
            error_msg="Failed to create commands directory",
        )
        self.communicate_with_handling(
            "touch /root/commands/__init__.py",
            error_msg="Failed to create __init__.py",
        )
        self.communicate_with_handling(
            "export PATH=$PATH:/root/commands",
            error_msg="Failed to add commands directory to PATH",
        )

    def _communicate_experimental(
        self,
        input: str,
        timeout_duration=25,
    ) -> str:
        """Experimental version of `_communicate`"""

        command_suffix = f"echo {PROCESS_DONE_MARKER_START}$?{PROCESS_DONE_MARKER_END}\n"
        try:
            self.returncode = None
            cmd = input if input.endswith("\n") else input + "\n"
            cmd += command_suffix
            os.write(self.container.stdin.fileno(), cmd.encode())
            time.sleep(0.03)
            self.container.stdin.flush()
        except BrokenPipeError:
            traceback.print_exc()
            self.logger.error("Failed to communicate with container. Check docker logs for more information.")
            msg = "Failed to communicate with container"
            raise RuntimeError(msg)

        buffer, exit_code = read_with_timeout_experimental(self.container, timeout_duration)
        self.returncode = int(exit_code)
        return buffer

    def _communicate(
        self,
        input: str,
        timeout_duration=25,
    ) -> str:
        if "SWE_AGENT_EXPERIMENTAL_COMMUNICATE" in Config():
            return self._communicate_experimental(input, timeout_duration)
        try:
            self.returncode = None
            cmd = input if input.endswith("\n") else input + "\n"
            os.write(self.container.stdin.fileno(), cmd.encode())
            time.sleep(0.1)
            self.container.stdin.flush()
        except BrokenPipeError:
            traceback.print_exc()
            self.logger.error("Failed to communicate with container. Check docker logs for more information.")
            msg = "Failed to communicate with container"
            raise RuntimeError(msg)
        try:
            buffer = read_with_timeout(self.container, self.get_pids, timeout_duration)
            self.container.stdin.write("echo $?\n")
            time.sleep(0.1)
            self.container.stdin.flush()
            exit_code = read_with_timeout(self.container, self.get_pids, 5).strip()
        except Exception as e:
            self.logger.error(f"Read with timeout failed on input:\n---\n{input}\n---")
            raise e
        if not exit_code.isdigit():
            msg = f"Container crashed. Failed to get exit code. Output:\n---\n{buffer}\n---"
            raise RuntimeError(msg)
        self.returncode = int(exit_code)
        return buffer

    def _check_syntax(self, input: str):
        """
        Saves environment variables to file
        """
        output = self._communicate(f"/bin/bash -n <<'EOF'\n{input}\nEOF\n")
        return output, self.returncode == 0

    def communicate(
        self,
        input: str,
        timeout_duration=25,
    ) -> str:
        """
        Sends input to container and returns output

        Args:
            input (`str`) - input to send to container

        Returns:
            output (`str`) - output from container
        """
        if input.strip() != "exit":
            output, valid = self._check_syntax(input)
            if not valid:
                return output  # shows syntax errors
            output = self._communicate(
                input,
                timeout_duration=timeout_duration,
            )
            self.communicate_output = output
            return output
        else:
            self.container.terminate()
            self.returncode = 0
            self.communicate_output = ""
            return ""

    def communicate_with_handling(self, input: str, error_msg: str, timeout_duration=25) -> str:
        """
        Wrapper for communicate function that raises error if return code is non-zero
        """
        logs = self.communicate(input, timeout_duration=timeout_duration)
        if self.returncode != 0:
            self.logger.error(f"{error_msg}: {logs}")
            self.close()
            msg = f"{error_msg}: {logs}"
            raise RuntimeError(msg)
        return logs

    def get_available_actions(self) -> list[str]:
        """
        Returns list of available actions in current environment state
        """
        return []

    def get_pids(self, all_pids=False) -> list[str]:
        """
        Gets list of processes running inside docker container
        """
        pids = self.container_obj.exec_run("ps -eo pid,comm --no-headers").output.decode().split("\n")
        pids = [x.split() for x in pids if x]
        if not all_pids:
            pids = [x for x in pids if x[1] != "ps" and x[0] not in self.parent_pids]
        return pids

    def get_submission(self, output: str) -> str:
        """
        Function for extracting diff patch submission at the end of an episode.

        Args:
            output (`str`) - `submit` observation
        Returns:
            submission (`str`) - diff patch submission
        """
        pattern = r"\<\<SUBMISSION\|\|(.*)\|\|SUBMISSION\>\>"
        match = re.search(pattern, output, re.DOTALL)
        if match is None:
            return None
        return match.group(1)

    def run_shell_script(self, script_path: Path, *, location: str) -> None:
        """Run custom script supplied by user at `script_path`

        Args:
            location: location of script file 'host' or 'container'
        """
        if location == "host":
            return self._run_shell_script_host(script_path)
        elif location == "container":
            raise NotImplementedError
        msg = f"Invalid 'location': {location}"
        raise ValueError(msg)

    def _run_shell_script_host(self, script_path: Path) -> None:
        """Run shell script file (located on host) in container"""
        if not script_path.is_file():
            msg = f"Script not found at {script_path}"
            raise FileNotFoundError(msg)
        shell_commands = Path(script_path).read_text().splitlines()
        for i, cmd in enumerate(shell_commands):
            self.communicate_with_handling(
                cmd,
                error_msg=f"Failed to execute line {i}.",
                timeout_duration=LONG_TIMEOUT,
            )

    def install_env(self) -> None:
        """
        Creates conda environment and installs third party dependencies to allow code execution
        """
        assert self.record is not None  # mypy
        if (
            self.record["problem_statement_source"] != "swe-bench" or self.record["repo_type"] == "local"
        ) and self.args.environment_setup is None:
            logger.warning(
                "install_environment is set to True, but the data path is a GitHub URL "
                "without an environment config file (environment_config key/flag). "
                "Skipping conda environment installation."
            )
            return
        for hook in self.hooks:
            hook.on_install_env_started()
        if self.args.environment_setup is not None:
            assert isinstance(self.args.environment_setup, (str, os.PathLike))
            if Path(self.args.environment_setup).suffix in [".yml", ".yaml"]:
                try:
                    install_configs = yaml.safe_load(Path(self.args.environment_setup).read_text())
                except Exception as e:
                    msg = "Environment config file needs to be a yaml file"
                    raise ValueError(msg) from e
            elif Path(self.args.environment_setup).suffix == ".sh":
                self.run_shell_script(Path(self.args.environment_setup), location="host")
                return
            else:
                msg = "Environment config file needs to be a yaml file or shell script"
                raise ValueError(msg)
        else:
            try:
                install_configs = MAP_VERSION_TO_INSTALL[self.record["repo"]][str(self.record["version"])]
            except KeyError as e:
                msg = (
                    "Tried to look up install configs in swe-bench, but failed. "
                    "You can set a custom environment config with the environment_config key/flag."
                )
                raise ValueError(msg) from e
        # Create environment if does not exist yet
        env_name = f"{self._repo_name}__{self.record['version']}"
        env_check = self.communicate(f"conda env list | grep {env_name}", timeout_duration=LONG_TIMEOUT)
        if env_check.strip() == "":
            self.logger.info(f"{env_name} conda env not found, creating...")
            packages = install_configs.get("packages", "")
            if packages == "requirements.txt":
                # Create conda environment
                self.communicate_with_handling(
                    f"conda create -n {env_name} python={install_configs['python']} -y",
                    error_msg="Failed to create conda environment",
                    timeout_duration=LONG_TIMEOUT,
                )
                # Write reqs to requirements.txt in docker container
                content_reqs = get_requirements(self.record)
                copy_file_to_container(self.container_obj, content_reqs, PATH_TO_REQS)
                # Create conda environment + install reqs
                self.communicate_with_handling(
                    f"conda activate {env_name}",
                    error_msg="Failed to activate conda environment",
                )
                self.communicate_with_handling(
                    f"pip install -r {PATH_TO_REQS}",
                    error_msg="Failed to install requirements.txt",
                    timeout_duration=LONG_TIMEOUT,
                )
                self.communicate(f"rm {PATH_TO_REQS}")
            elif packages == "environment.yml":
                # Write environment.yml to file
                if install_configs.get("no_use_env", False):
                    content_env_yml = get_environment_yml(self.record, env_name)
                else:
                    content_env_yml = get_environment_yml(
                        self.record, env_name, python_version=install_configs["python"]
                    )
                copy_file_to_container(self.container_obj, content_env_yml, PATH_TO_ENV_YML)
                if install_configs.get("no_use_env", False):
                    # Create conda environment
                    self.communicate_with_handling(
                        f"conda create -c conda-forge -n {env_name} python={install_configs['python']} -y",
                        error_msg="Failed to create conda environment",
                        timeout_duration=LONG_TIMEOUT,
                    )
                    # Install packages
                    self.communicate_with_handling(
                        f"conda env update -f {PATH_TO_ENV_YML}",
                        error_msg="Failed to install environment.yml",
                        timeout_duration=LONG_TIMEOUT,
                    )
                else:
                    # Create environment + install packages
                    self.communicate_with_handling(
                        f"conda env create --file {PATH_TO_ENV_YML}",
                        error_msg="Failed to create conda environment with environment.yml",
                        timeout_duration=LONG_TIMEOUT,
                    )
                self.communicate(f"rm {PATH_TO_ENV_YML}")
            else:
                # Create environment + install packages
                self.communicate_with_handling(
                    f"conda create -n {env_name} python={install_configs['python']} {packages} -y",
                    error_msg="Failed to create conda environment",
                    timeout_duration=LONG_TIMEOUT,
                )
            # Install extra pip packages if specified
            if install_configs.get("pip_packages", False):
                self.communicate_with_handling(
                    f"source activate {env_name} && pip install {' '.join(install_configs['pip_packages'])}",
                    error_msg="Failed to install pip packages",
                    timeout_duration=LONG_TIMEOUT,
                )

        # Activate environment
        self.communicate_with_handling(f"conda activate {env_name}", error_msg="Failed to activate conda environment")

        # Install repo at base commit
        if install_configs.get("pre_install", False):
            self.logger.info("Running pre-install commands...")
            for pre_install_cmd in install_configs["pre_install"]:
                self.communicate_with_handling(
                    pre_install_cmd,
                    error_msg="Pre-install commands failed to execute successfully",
                )
        self.logger.info(f"Installing {self._repo_name} at base commit...")
        if install_configs.get("install", False):
            install_cmd = install_configs["install"]
            self.communicate_with_handling(
                install_cmd, error_msg="Install command failed to execute successfully", timeout_duration=LONG_TIMEOUT
            )
        if install_configs.get("post_install", False):
            self.logger.info("Running post-install commands...")
            for post_install_cmd in install_configs["post_install"]:
                self.communicate_with_handling(
                    post_install_cmd,
                    error_msg="Post-install commands failed to execute successfully",
                )

    def add_commands(self, commands: list[dict]) -> None:
        """
        Adds custom commands to container
        """
        for command in commands:
            name = command["name"]
            contents = command["contents"]
            copy_file_to_container(self.container_obj, contents, f"/root/commands/{name}")
            if command["type"] == "source_file":
                self.communicate_with_handling(
                    f"source /root/commands/{name}",
                    error_msg=(
                        f"Failed to source {name}. If you meant to make a script,"
                        " start the file with a shebang (e.g. #!/usr/bin/env python)."
                    ),
                )
            elif command["type"] == "script":
                self.communicate_with_handling(
                    f"chmod +x /root/commands/{name}",
                    error_msg=f"Failed to chmod {name}",
                )
            elif command["type"] == "utility":
                # nothing to do for utility scripts
                pass
            else:
                msg = f"Invalid command type: {command['type']}"
                raise ValueError(msg)

    def interrupt(self):
        """
        Send interrupt signal to container and exhaust stdout buffer with a communicate call
        """
        pids = self.get_pids()
        for pid, cmd in pids:
            if pid not in self.parent_pids and cmd != "ps":
                self.container_obj.exec_run(f"kill -9 {pid}")
        try:
            _ = read_with_timeout(self.container, self.get_pids, 20)
        except TimeoutError:
            pass
        try:
            output = self.communicate(input="echo 'interrupted'", timeout_duration=5)
            assert output.strip().endswith("interrupted"), "container health check failed"
        except TimeoutError:
            msg = "Failed to interrupt container"
            raise RuntimeError(msg)

    def open_pr(self, *, trajectory, _dry_run: bool = False):
        """Create PR to repository

        Args:
            trajectory: Trajectory of actions taken by the agent
            _dry_run: Whether to actually push anything or just simulate it
        """
        logger.info("Opening PR")
        # todo: have better way of handling this
        # Adding random string suffix to avoid name conflicts if we had a previously failed run
        issue_url = self.args.data_path
        try:
            issue = get_gh_issue_data(issue_url, token=self._github_token)
        except InvalidGithubURL as e:
            msg = "Data path must be a github issue URL if --open_pr is set."
            raise ValueError(msg) from e
        branch_name = f"swe-agent-fix-#{issue.number}-" + str(random.random())[2:10]

        self.communicate_with_handling(
            input="rm -f model.patch",
            error_msg="Failed to remove model patch",
            timeout_duration=10,
        )
        self.communicate_with_handling(
            input=f"git checkout -b {branch_name}",
            error_msg="Failed to switch to new branch",
            timeout_duration=10,
        )
        self.communicate_with_handling(
            input="git add .",
            error_msg="Failed to add commits",
            timeout_duration=10,
        )
        dry_run_flag = "--allow-empty" if _dry_run else ""
        self.communicate_with_handling(
            input=f"git commit -m 'Fix: {issue.title}' -m 'Closes #{issue.number}' {dry_run_flag}",
            error_msg="Failed to commit changes",
            timeout_duration=10,
        )

        owner, repo, _ = parse_gh_issue_url(issue_url)
        # If `--repo_path` was specified with a different github URL, then the record will contain
        # the forking user
        assert self.record is not None
        if not self.record["repo_type"] == "github":
            # We already validated that `--data_path` is a github issue URL
            # so this is the only case where we can reach here
            msg = "--repo_path must point to a github URL if --open_pr is set"
            raise ValueError(msg)
        forker, _ = self.record["repo"].split("/")
        head = branch_name
        remote = "origin"
        if forker != owner:
            head = f"{forker}:{branch_name}"
            token_prefix = ""
            if self._github_token:
                token_prefix = f"{self._github_token}@"
            fork_url = f"https://{token_prefix}github.com/{forker}/{repo}.git"
            logger.debug(f"Using fork: {fork_url}")
            self.communicate_with_handling(
                input=f"git remote add fork {fork_url}",
                error_msg="Failed to create new git remote",
                timeout_duration=10,
            )
            remote = "fork"
        dry_run_prefix = "echo " if _dry_run else ""
        self.communicate_with_handling(
            input=f"{dry_run_prefix} git push {remote} {branch_name}",
            error_msg=(
                "Failed to push branch to remote. Please check your token and permissions. "
                "You might want to push to a fork with the push_gh_repo_url option."
            ),
            timeout_duration=10,
        )
        body = (
            f"This is a PR opened by AI tool [SWE Agent](https://github.com/princeton-nlp/SWE-agent/) "
            f"to close [#{issue.number}]({issue_url}) ({issue.title}).\n\nCloses #{issue.number}."
        )
        body += "\n\n" + format_trajectory_markdown(trajectory)
        api = GhApi(token=self._github_token)
        if not _dry_run:
            pr_info = api.pulls.create(
                owner=owner,
                repo=repo,
                title=f"SWE-agent[bot] PR to fix: {issue.title}",
                head=head,
                base="main",
                body=body,
                draft=True,
            )
            logger.info(
                f"🎉 PR created as a draft at {pr_info.html_url}. Please review it carefully, push "
                "any required changes onto the branch and then click "
                "'Ready for Review' to bring it to the attention of the maintainers."
            )
