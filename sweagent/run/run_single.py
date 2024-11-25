"""[cyan][bold]Run SWE-agent on a single instance taken from github or similar.[/bold][/cyan]

[cyan][bold]=== BASICOPTIONS ===[/bold][/cyan]

  -h --help           Show help text and exit
  --config CONFIG     Load additional config files. Use this option multiple times to load
                      multiple files, e.g., --config config1.yaml --config config2.yaml
  --no_config_file    Do not load default config file when no config file is provided
  --print_options     Print all additional configuration options that can be set via CLI and exit
  [cyan][bold]--... Many more options[/cyan][/bold] (run `sweagent run --print_options` for a complete overview)

[cyan][bold]=== EXAMPLES ===[/bold][/cyan]

Basic usage: Run over a [bold][cyan]github issue[/bold][/cyan][green]:

sweagent run --config config/config.yaml --agent.model.name "gpt-4o" \\
    --env.repo.github_url=https://github.com/SWE-agent/test-repo/ \\
    --problem_statement.github_url=https://github.com/SWE-agent/test-repo/issues/1
[/green]

By default this will start a docker container and run the agent in there.
You can set the image with [green]--env.docker.image[/green].

Here's an example that uses [bold][cyan]modal[/bold][/cyan] instead of docker and also a [bold][cyan]local repository[/bold][/cyan]:

[green]sweagent run --config config/config.yaml --agent.model.name "gpt-4o" \\
    --env.deployment.type=modal --env.repo.path /path/to/repo \\
    --problem_statement.path=path/to/problem_statement.md
[/green]

[cyan][bold]=== MORE ===[/bold][/cyan]

To find out all command line options, run [green]sweagent run --print_options[/green]!

Want to run over more than one issue? Check out the [bold][cyan]batch mode[/bold][/cyan]: [green]sweagent run-batch --help[/green]!
"""

import getpass
import sys
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.environment.config.problem_statement import (
    EmptyProblemStatement,
    ProblemStatement,
    ProblemStatementConfig,
)
from sweagent.environment.swe_env import EnvironmentConfig, SWEEnv
from sweagent.run.common import BasicCLI, save_predictions
from sweagent.run.hooks.abstract import CombinedRunHooks, RunHook
from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
from sweagent.run.hooks.open_pr import OpenPRConfig, OpenPRHook
from sweagent.utils.config import load_environment_variables
from sweagent.utils.log import add_file_handler, get_logger


class RunSingleActionConfig(BaseModel, cli_implicit_flags=True):
    """Run real-life actions (opening PRs, etc.) if we can solve the issue."""

    # Open a PR with the patch if we can solve the issue
    open_pr: bool = False
    pr_config: OpenPRConfig = Field(default_factory=OpenPRConfig)
    # When working with local repository: Apply patch
    apply_patch_locally: bool = False


class RunSingleConfig(BaseSettings, cli_implicit_flags=True):
    env: EnvironmentConfig = Field(default_factory=EnvironmentConfig, description="Environment options.")
    agent: AgentConfig = Field(description="Agent options.")
    problem_statement: ProblemStatementConfig = Field(
        default_factory=EmptyProblemStatement, description="Problem statement options."
    )
    output_dir: Path = Field(default=Path("DEFAULT"), description="Output directory.")

    actions: RunSingleActionConfig = Field(default_factory=RunSingleActionConfig)

    env_var_path: Path | None = None
    """Path to a .env file to load environment variables from."""

    # pydantic config
    model_config = ConfigDict(extra="forbid")  # type: ignore

    def set_default_output_dir(self) -> None:
        # Needs to be called explicitly, because self._config_files will be setup
        # post-init.
        if self.output_dir == Path("DEFAULT"):
            user_id = getpass.getuser()
            problem_id = self.problem_statement.id
            model_id = self.agent.model.id
            config_file = getattr(self, "_config_files", ["no_config"])[0]
            if isinstance(config_file, Path):
                config_file = config_file.stem
            self.output_dir = Path.cwd() / "trajectories" / user_id / f"{config_file}__{model_id}___{problem_id}"


class RunSingle:
    def __init__(
        self,
        env: SWEEnv,
        agent: Agent,
        problem_statement: ProblemStatement | ProblemStatementConfig,
        *,
        output_dir: Path = Path("."),
        hooks: list[RunHook] | None = None,
        actions: RunSingleActionConfig | None = None,
    ):
        """Note: When initializing this class, make sure to add the hooks that are required by your actions.
        See `from_config` for an example.
        """
        self.logger = get_logger("swea-run", emoji="🏃")
        instance_id = problem_statement.id
        _log_filename_template = f"{instance_id}.{{level}}.log"
        for level in ["trace", "debug", "info"]:
            add_file_handler(
                output_dir / _log_filename_template.format(level=level),
                level=level,
                id_=f"{instance_id}-{level}",
            )
        self.env = env
        self.agent = agent
        self.output_dir = output_dir
        self._hooks = []
        if actions is not None:
            actions = RunSingleActionConfig()
        self.actions = actions
        self._chooks = CombinedRunHooks()
        self.problem_statement = problem_statement
        for hook in hooks or []:
            self.add_hook(hook)

    @property
    def hooks(self) -> list[RunHook]:
        return self._chooks.hooks

    @classmethod
    def from_config(cls, config: RunSingleConfig) -> Self:
        load_environment_variables(config.env_var_path)
        config.set_default_output_dir()
        config.output_dir.mkdir(parents=True, exist_ok=True)
        agent = Agent.from_config(config.agent)
        agent.replay_config = config
        self = cls(
            env=SWEEnv.from_config(config.env),
            agent=agent,
            problem_statement=config.problem_statement,
            output_dir=config.output_dir,
            actions=config.actions,
        )
        self.add_hook(SaveApplyPatchHook(apply_patch_locally=config.actions.apply_patch_locally))
        if config.actions.open_pr:
            self.logger.debug("Adding OpenPRHook")
            self.add_hook(OpenPRHook(config.actions.pr_config))
        return self

    def add_hook(self, hook: RunHook) -> None:
        hook.on_init(run=self)
        self._chooks.add_hook(hook)

    def run(self):
        self._chooks.on_start()
        self.logger.info("Starting environment")
        self.env.start()
        self.logger.info("Running agent")
        self._chooks.on_instance_start(index=0, env=self.env, problem_statement=self.problem_statement)
        result = self.agent.run(
            problem_statement=self.problem_statement,
            env=self.env,
            output_dir=Path(self.output_dir),
        )
        self._chooks.on_instance_completed(result=result)
        self.logger.info("Done")
        self._chooks.on_end()
        save_predictions(self.output_dir, self.problem_statement.id, result)
        self.env.close()


def run_from_config(config: RunSingleConfig):
    RunSingle.from_config(config).run()


def run_from_cli(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    run_from_config(BasicCLI(RunSingleConfig, help_text=__doc__).get_config(args))  # type: ignore


if __name__ == "__main__":
    run_from_cli()
