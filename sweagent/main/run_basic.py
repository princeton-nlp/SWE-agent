"""Run in human mode without any complicated env setup.
This is mostly for debugging and development.
"""

from argparse import ArgumentParser
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, CliApp

from sweagent import CONFIG_DIR
from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentConfig, SWEEnv
from sweagent.utils.log import get_logger


class BasicRunArguments(BaseSettings):
    env: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    agent: AgentConfig = AgentConfig(
        model=ModelArguments(name="human"), next_step_template="Observation: {observation}"
    )
    traj_dir: str = "."


# todo: add hooks
class BasicMain:
    def __init__(self, args: BasicRunArguments):
        self.args = args
        self.logger = get_logger("PlaygroundMain")
        self.logger.info("Initializing environment")
        self.env = SWEEnv(args.env)
        self.logger.info("Initializing agent")
        self.agent = Agent("main", args.agent)

    def main(self):
        self.logger.info("Resetting environment")
        observation, info = self.env.reset()
        self.logger.info("Running agent")
        info, trajectory = self.agent.run(
            setup_args={"problem_statement": self.args.env.instance.get_problem_statement()},
            env=self.env,
            observation=observation,
            traj_dir=Path(self.args.traj_dir),
            return_type="info_trajectory",
        )
        self.logger.info("Done")


def main(args: BasicRunArguments):
    BasicMain(args).main()


class BasicCLI:
    def __init__(self, arg_type: type[BaseSettings]):
        self.arg_type = arg_type

    def get_args(self, args=None) -> BaseSettings:
        # The defaults if no config file is provided
        # Otherwise, the configs from the respective classes will be used
        parser = ArgumentParser(description=__doc__)
        parser.add_argument(
            "--config",
            type=str,
            action="append",
            default=[],
            help="Load additional config files. Use this option multiple times to load multiple files, e.g., --config config1.yaml --config config2.yaml",
        )
        parser.add_argument(
            "--no-config-file",
            action="store_true",
            help="Do not load default config file when no config file is provided",
        )
        parser.add_argument(
            "--print-options",
            action="store_true",
            help="Print all additional configuration options that can be set via CLI and exit",
        )
        parser.add_argument("--print-config", action="store_true", help="Print the final config and exit")
        cli_args, remaining_args = parser.parse_known_args(args)

        if cli_args.print_options:
            CliApp.run(self.arg_type, ["--help"])
            exit(0)

        config_merged = {}
        if cli_args.config:
            for _f in cli_args.config:
                _loaded = yaml.safe_load(Path(_f).read_text())
                config_merged.update(_loaded)
        elif not cli_args.no_config_file:
            config_merged = yaml.safe_load((CONFIG_DIR / "default.yaml").read_text())
        else:
            config_merged = self.arg_type().model_dump()

        # args = ScriptArguments.model_validate(config_merged)
        print("-------")
        print(remaining_args)
        print("-------")
        args = CliApp.run(self.arg_type, remaining_args, **config_merged)  # type: ignore
        if cli_args.print_config:  # type: ignore
            print(yaml.dump(args.model_dump()))
            exit(0)
        return args


if __name__ == "__main__":
    main(BasicCLI(BasicRunArguments).get_args())  # type: ignore
