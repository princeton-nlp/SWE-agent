import asyncio
import logging
import shlex
from pathlib import PurePath
from typing import Self

from pydantic import BaseModel, ConfigDict, Field
from swerex.deployment.abstract import AbstractDeployment
from swerex.deployment.config import DeploymentConfig, DockerDeploymentConfig, get_deployment
from swerex.runtime.abstract import BashAction, CreateBashSessionRequest

from sweagent.environment.config.repo import Repo, RepoConfig
from sweagent.environment.hooks.abstract import CombinedEnvHooks, EnvHook
from sweagent.utils.log import get_logger


class EnvironmentConfig(BaseModel):
    """Configure data sources and setup instructions for the environment in which we solve the tasks."""

    deployment: DeploymentConfig = Field(
        default_factory=lambda: DockerDeploymentConfig(image="sweagent/swe-agent:latest")
    )
    repo: RepoConfig | None = None
    # fixme: Actually run these
    startup_commands: list[str] = []
    """Execute these commands before starting to run the agent. They will be executed in the same
    shell as the agent."""

    # pydantic config
    model_config = ConfigDict(extra="forbid")


class SWEEnv:
    name = "swe_main"

    def __init__(
        self,
        *,
        deployment: AbstractDeployment,
        repo: Repo | RepoConfig | None,
        startup_commands: list[str],
        hooks: list[EnvHook] | None = None,
    ):
        """This class represents the environment in which we solve the tasks."""
        super().__init__()
        self.deployment = deployment
        self.repo = repo
        self._startup_commands = startup_commands
        self.logger = get_logger("swe_env", emoji="🌱")

        self.clean_multi_line_functions = lambda x: x
        self._chook = CombinedEnvHooks()
        for hook in hooks or []:
            self.add_hook(hook)

    @classmethod
    def from_config(cls, config: EnvironmentConfig) -> Self:
        return cls(
            deployment=get_deployment(config.deployment),
            repo=config.repo,
            startup_commands=config.startup_commands,
        )

    def add_hook(self, hook: EnvHook) -> None:
        """Add `EnvHook` to the environment.

        This allows to inject custom functionality at different stages of the environment
        lifecycle, in particular to connect SWE-agent to a new interface (like a GUI).
        """
        hook.on_init(env=self)
        self._chook.add_hook(hook)

    def start(self) -> None:
        """Start the environment and reset it to a clean state."""
        self._init_deployment()
        self.reset()

    def _copy_repo(self) -> None:
        """Clone/copy repository/codebase in container"""
        if self.repo is None:
            return

        folders = self.communicate(input="ls", check=True).split("\n")
        if self.repo.repo_name in folders:
            return

        self._chook.on_copy_repo_started(repo=self.repo)
        self.repo.copy(self.deployment)

    # todo: Get rid of return type here?
    def reset(self) -> tuple[str | None, dict]:
        """Reset the environment to a clean state.
        Gets called by `start`, but can also be called independently to reset the
        environment to a clean state before a new attempt.

        Returns:
            observation: output from container
            info: additional information (e.g. debugging information)
        """
        info = {}
        self.communicate(input="cd /", check=True)
        self._copy_repo()
        self._reset_repository()
        self._chook.on_environment_startup()
        return None, info

    def _reset_repository(self) -> None:
        """Clean repository of any modifications + Checkout base commit"""
        if self.repo is not None:
            self.logger.debug("Resetting repository %s to commit %s", self.repo.repo_name, self.repo.base_commit)
            startup_commands = [
                f"cd /{self.repo.repo_name}",
                "export ROOT=$(pwd -P)",
                "git status",
                "git restore .",
                f"git reset --hard {self.repo.base_commit}",
                "git clean -fdxq",
            ]
            self.communicate(
                input=" && ".join(startup_commands),
                check=True,
                error_msg="Failed to clean repository",
            )

    def close(self) -> None:
        """Shoutdown SWE-ReX deployment etc."""
        self.logger.info("Beginning environment shutdown...")
        asyncio.run(self.deployment.stop())
        self._chook.on_close()

    # MARK: Helper functions #

    def _init_deployment(
        self,
    ) -> None:
        """Handles container initialization. Defines container name and creates it.
        If cached_image is provided, it will use that image name instead of the default.
        """
        self._chook.on_start_deployment()
        asyncio.run(self.deployment.start())
        asyncio.run(self.deployment.runtime.create_session(CreateBashSessionRequest(startup_source=["/root/.bashrc"])))
        self.logger.info("Environment Initialized")

    def communicate(
        self,
        input: str,
        timeout: int | float = 25,
        *,
        set_last_action: bool = False,
        check: bool = False,
        error_msg: str = "Command failed",
    ) -> str:
        """Executes a command in the running shell. The details of this are handled by
        the SWE-ReX deployment/runtime.

        Args:
            input: input to send to container
            timeout_duration: duration to wait for output
            set_last_action: whether to set the LAST_ACTION environment variable
            check: whether to raise an error if the exit code is non-zero
            error_msg: error message to raise if the command fails

        Returns:
            output: output from container
        """
        self.logger.log(logging.TRACE, "Input:\n%s", input)  # type: ignore
        r = asyncio.run(self.deployment.runtime.run_in_session(BashAction(command=input, timeout=timeout)))
        output = r.output
        self.logger.log(logging.TRACE, "Output:\n%s", output)  # type: ignore
        if check and r.exit_code != 0:
            self.logger.error(f"{error_msg}:\n{output}")
            self.close()
            msg = f"Command {input!r} failed ({r.exit_code=}): {error_msg}"
            raise RuntimeError(msg)
        # todo: What do we do with this?
        if set_last_action:
            # Cannot merge this with last command, because of multiline command
            # handling.
            last_action_string = shlex.quote(input.strip())
            input = f"export LAST_ACTION={last_action_string}"
            r = asyncio.run(self.deployment.runtime.run_in_session(BashAction(command=input, timeout=1)))
        return output

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
