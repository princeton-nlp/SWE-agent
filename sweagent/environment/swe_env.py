from __future__ import annotations

import asyncio
import logging
import re
import shlex
from pathlib import PurePath
from typing import Self

from pydantic import BaseModel, Field
from swerex.deployment.abstract import AbstractDeployment
from swerex.runtime.abstract import BashAction, CreateBashSessionRequest, WriteFileRequest

from sweagent.environment.config.deployment import DeploymentConfig, DockerDeploymentConfig
from sweagent.environment.config.repo import Repo, RepoConfig
from sweagent.environment.hooks.abstract import EnvHook
from sweagent.types import AgentInfo
from sweagent.utils.config import keys_config
from sweagent.utils.log import get_logger
from sweagent.utils.patch_formatter import PatchFormatter

LONG_TIMEOUT = float(keys_config.get("SWE_AGENT_ENV_LONG_TIMEOUT", 500))
AGENT_ACTION_TIMEOUT = float(keys_config.get("SWE_AGENT_ACTION_TIMEOUT", 25))
AGENT_ACTION_NO_OUTPUT_TIMEOUT = float(keys_config.get("SWE_AGENT_ACTION_NO_OUTPUT_TIMEOUT", AGENT_ACTION_TIMEOUT))


class EnvironmentConfig(BaseModel):
    """Configure data sources and setup instructions for the environment in which we solve the tasks."""

    deployment: DeploymentConfig = Field(default_factory=DockerDeploymentConfig)
    repo: RepoConfig | None = None
    startup_commands: list[str] = []


class SWEEnv:
    name = "swe_main"

    def __init__(
        self,
        *,
        deployment: AbstractDeployment,
        repo: Repo | None,
        startup_commands: list[str],
        hooks: list[EnvHook] | None = None,
        _catch_errors: bool = False,
        _always_require_zero_exit_code: bool = False,
    ):
        """This class represents the environment in which we solve the tasks."""
        super().__init__()
        self._catch_errors = _catch_errors
        self._require_zero_exit_code = _always_require_zero_exit_code
        self.deployment = deployment
        self.repo = repo
        self._startup_commands = startup_commands
        self.logger = get_logger("swe_env", emoji="🌱")

        self.clean_multi_line_functions = lambda x: x
        self._hooks: list[EnvHook] = []
        for hook in hooks or []:
            self.add_hook(hook)

    def start(self) -> None:
        """Start the environment"""
        self._init_container()
        self._init_scripts()

    @classmethod
    def from_config(cls, config: EnvironmentConfig) -> Self:
        return cls(
            deployment=config.deployment.get_deployment(),
            repo=config.repo,
            startup_commands=config.startup_commands,
        )

    @property
    def hooks(self) -> list[EnvHook]:
        return self._hooks

    def add_hook(self, hook: EnvHook) -> None:
        """Add `EnvHook` to the environment.

        This allows to inject custom functionality at different stages of the environment
        lifecycle, in particular to connect SWE-agent to a new interface (like a GUI).
        """
        hook.on_init(env=self)
        self._hooks.append(hook)

    def _fire_hooks(self, hook_name: str, *args, **kwargs) -> None:
        for hook in self.hooks:
            getattr(hook, hook_name)(*args, **kwargs)

    # @property
    # def _repo_name(self) -> str:
    #     """Name of the local copy of the repository"""
    #     return self.record["repo"].replace("/", "__").replace(" ", "-").replace("'", "")

    # todo: Ideally move that to the RepoClasses
    def _copy_repo(self) -> None:
        """Clone/copy repository/codebase in container"""
        if self.repo is None:
            return

        folders = self.communicate(input="ls").split("\n")
        if self.repo.repo_name in folders:
            return

        self._fire_hooks("on_copy_repo_started", self.repo)
        self.repo.copy(self.deployment)

    # todo: have named return type here
    def reset(self) -> tuple[str | None, dict]:
        """Reset the container between each task instance.

        * Clones instance's repository
        * Cleans repository of prior modifications
        * Resets environment variables
        * Check out base commit

        Args:
            index: index of task instance to reset to

        Returns:
            observation: output from container
            info: additional information (e.g. debugging information)
        """
        info = {}

        ### Reset Container ###
        # self._init_docker_compose()

        # Init docker network
        # self._init_docker_network()

        # Clone repository if not already cloned
        self.communicate(input="cd /")
        self._copy_repo()

        self._reset_repository()
        self._reset_environment_variables()

        # Set up environment
        # self.communicate_with_handling(
        #     "source /root/miniconda3/etc/profile.d/conda.sh",
        #     error_msg="Failed to source conda",
        # )

        # system = self.communicate("uname -s").strip().lower()
        # arch = self.communicate("uname -m").strip().lower()
        # if system == "linux" and arch == "x86_64":
        #     self.communicate_with_handling(
        #         "apt update; apt install build-essential -y",
        #         error_msg="Failed to install build-essential",
        #         timeout_duration=LONG_TIMEOUT,
        #     )

        # Call install environment helper function if specified
        # if self.install_environment:
        self.on_environment_startup()
        # Install mypy for linting purposes
        # self.communicate_with_handling("pip install flake8", error_msg="Failed to install flake8 (lint library)")

        # Write any metadata to info if necessary
        return None, info

    def _reset_repository(self) -> None:
        """Clean repository of any modifications + Checkout base commit"""
        if self.repo is not None:
            startup_commands = [
                "echo -n > /root/files_to_edit.txt",
                f"cd /{self.repo.repo_name}",
                "export ROOT=$(pwd -P)",
            ]
            # if self.challenge is None:
            startup_commands += [
                "git status",
                "git restore .",
                f"git reset --hard {self.repo.base_commit}",
                "git clean -fdxq",
            ]
            self.communicate(
                input=" && ".join(startup_commands),
                require_zero=True,
                error_msg="Failed to clean repository",
            )

    def _reset_environment_variables(self) -> None:
        """Reset environment variables (`CURRENT_FILE`) etc. within container"""
        cmd = [
            'export CURRENT_FILE=""',
            "export CURRENT_LINE=0",
            "export SEARCH_RESULTS=()",
            "export SEARCH_FILES=()",
            "export SEARCH_INDEX=0",
        ]
        self.communicate(
            input=" && ".join(cmd),
            require_zero=True,
            error_msg="Failed to reset environment variables",
        )

    # todo: Shouldn't this be the same as reset meanwhile?
    def reset_for_new_attempt(
        self,
    ) -> None:
        """Compared to `reset`, which prepares the container for a new instance,
        this prepares the container for taking another shot at the same instance.
        """
        self._reset_repository()
        self._reset_environment_variables()

    def _get_edited_files_with_context(self, patch: str) -> dict[str, str]:
        """Get the edited files with context from the patch"""
        pf = PatchFormatter(patch, read_method=self.read_file) if patch else None
        out = {}
        for context_length in [30, 50, 70]:
            value = "Empty. No edited files found."
            if pf is not None:
                value = pf.get_files_str(original=False, context_length=context_length)
            out[f"edited_files{context_length}"] = value
        return out

    # todo: Have a return type here
    # todo: Break this up
    def step(self, action: str) -> tuple[str, int, bool, AgentInfo]:
        """Runs an action proposed by the agent in the environment and returns the corresponding output.

        Args:
            action: command to run in bash shell

        Returns:
            observation:  output from container
            reward: Always set to 0
            done: whether task is over
            info: additional information (e.g. debugging information)
        """
        info: AgentInfo = {}
        # Make sure to have the right keys even if the submission is missing/empty
        info.update(self._get_edited_files_with_context(patch=""))  # type: ignore

        observation = ""
        # Handle special actions
        action = action.strip()
        if action == "skip":
            observation = "Skipped"
            info["exit_status"] = "skipped"
            return observation, 0, True, info
        if action == "exit_forfeit":
            observation = "Exited"
            info["exit_status"] = action
            return observation, 0, True, info
        # todo: pull out a handle_exit_action function
        if action in {"exit_context", "exit_cost", "exit_error", "exit_format", "exit_api"}:
            try:
                observation = self.communicate(input="submit")
                submission = self.get_submission(observation)
                assert submission is not None and submission.strip() != "", AssertionError("No submission found.")
                self.logger.info(f"Found submission: {submission}")
                info["exit_status"] = f"submitted ({action})"
                info["submission"] = submission
                info.update(self._get_edited_files_with_context(patch=submission))  # type: ignore
                observation = "Exited (autosubmitted)"
                self.logger.info("Exiting with autosubmission")
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
            observation = self.communicate(
                input=action,
                timeout=AGENT_ACTION_TIMEOUT,
                set_last_action=True,
            )
        except RuntimeError as e:
            if not self._catch_errors:
                raise
            observation += e.args[1] if len(e.args) > 1 else ""
            observation += "\nCOMMAND FAILED TO EXECUTE. RESTARTING PROCESS."
            info["exit_status"] = "early_exit"
            self.logger.warning(f"Failed to execute command: {e}\nRESTARTING PROCESS.")
            self.reset_container()
            return observation, 0, True, info
        except Exception:
            if not self._catch_errors:
                raise
            observation += "\nEXECUTION FAILED OR COMMAND MALFORMED"
            self.logger.exception("Unknown exception")

        # Record submission and end episode if `submit` keyword found
        submission = self.get_submission(observation)
        if submission is not None:
            # if self.validate_submission(submission):
            self.logger.info(f"Found submission: {submission}")
            info["exit_status"] = "submitted"
            info["submission"] = submission if submission.strip() != "" else None
            info.update(self._get_edited_files_with_context(patch=submission))  # type: ignore
            observation = submission if submission.strip() != "" else ""
            return observation, 0, True, info

        return observation, 0, False, info

    def close(self) -> None:
        """Shoutdown SWE-ReX deployment etc."""
        self.logger.info("Beginning environment shutdown...")
        asyncio.run(self.deployment.stop())
        self._fire_hooks("on_close")

    # MARK: Helper functions #

    def reset_container(self) -> None:
        self.close()
        self._init_container()
        self._init_scripts()

    def _init_container(
        self,
    ) -> None:
        """Handles container initialization. Defines container name and creates it.
        If cached_image is provided, it will use that image name instead of the default.
        """
        asyncio.run(self.deployment.start())
        asyncio.run(self.deployment.runtime.create_session(CreateBashSessionRequest(startup_source=["/root/.bashrc"])))
        self.logger.info("Environment Initialized")

    def _init_scripts(self):
        """Initialize custom commands within container"""
        self.communicate(
            "mkdir -p /root/commands",
            require_zero=True,
            error_msg="Failed to create commands directory",
        )
        self.communicate(
            "touch /root/commands/__init__.py",
            require_zero=True,
            error_msg="Failed to create __init__.py",
        )
        self.communicate(
            "export PATH=$PATH:/root/commands",
            require_zero=True,
            error_msg="Failed to add commands directory to PATH",
        )

    def communicate(
        self,
        input: str,
        timeout: int | float = 25,
        *,
        set_last_action: bool = False,
        require_zero: bool = False,
        error_msg: str = "Command failed",
    ) -> str:
        """Executes a command in the running shell. The details of this are handled by
        the SWE-ReX deployment/runtime.

        Args:
            input: input to send to container
            timeout_duration: duration to wait for output
            set_last_action: whether to set the LAST_ACTION environment variable
            require_zero: whether to raise an error if the exit code is non-zero
            error_msg: error message to raise if the command fails

        Returns:
            output: output from container
        """
        if input.strip() == "exit":
            asyncio.run(self.deployment.stop())
            return ""

        self.logger.log(logging.TRACE, "Input:\n%s", input)  # type: ignore
        r = asyncio.run(self.deployment.runtime.run_in_session(BashAction(command=input, timeout=timeout)))
        output = r.output
        self.logger.log(logging.TRACE, "Output:\n%s", output)  # type: ignore
        if (self._require_zero_exit_code or require_zero) and r.exit_code != 0:
            self.logger.error(f"{error_msg}: {output}")
            self.close()
            msg = f"{error_msg} (command: {input})"
            raise RuntimeError(msg)
        # todo: What do we do with this?
        if set_last_action:
            # Cannot merge this with last command, because of multiline command
            # handling.
            last_action_string = shlex.quote(input.strip())
            input = f"export LAST_ACTION={last_action_string}"
            r = asyncio.run(self.deployment.runtime.run_in_session(BashAction(command=input, timeout=1)))
        return output

    def get_available_actions(self) -> list[str]:
        """Returns list of available actions in current environment state

        Currently not in use.
        """
        return []

    def get_submission(self, output: str) -> str | None:
        """Function for extracting diff patch submission at the end of an episode.

        Args:
            output: `submit` observation

        Returns:
            submission: diff patch submission
        """
        pattern = r"\<\<SUBMISSION\|\|(.*)\|\|SUBMISSION\>\>"
        match = re.search(pattern, output, re.DOTALL)
        if match is None:
            return None
        return match.group(1)

    def on_environment_startup(self) -> None:
        """Creates conda environment and installs third party dependencies to allow code execution"""
        self._fire_hooks("on_environment_startup")

    def add_commands(self, commands: list[dict]) -> None:
        """Adds custom commands to container"""
        for command in commands:
            name = command["name"]
            contents = command["contents"]
            asyncio.run(
                self.deployment.runtime.write_file(WriteFileRequest(content=contents, path=f"/root/commands/{name}"))
            )
            if command["type"] == "source_file":
                self.communicate(
                    f"source /root/commands/{name}",
                    require_zero=True,
                    error_msg=(
                        f"Failed to source {name}. If you meant to make a script,"
                        " start the file with a shebang (e.g. #!/usr/bin/env python)."
                    ),
                )
            elif command["type"] == "script":
                self.communicate(
                    f"chmod +x /root/commands/{name}",
                    require_zero=True,
                    error_msg=f"Failed to chmod {name}",
                )
            elif command["type"] == "utility":
                # nothing to do for utility scripts
                pass
            else:
                msg = f"Invalid command type: {command['type']}"
                raise ValueError(msg)

    # todo: Use the runtime for this instead
    def read_file(self, path: str | PurePath) -> str:
        """Read file contents from container

        Args:
            path: Path to file relative to repository root

        Returns:
            file_contents: Contents of file as string
        """
        if self.repo is None:
            msg = "Repository not set, cannot read file"
            raise ValueError(msg)

        path_in_container = f"/{self.repo.repo_name}/{path}"
        return self.communicate(f"cat {str(path_in_container)}")
