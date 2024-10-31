"""Common functionality for the run scripts."""

from argparse import ArgumentParser
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, CliApp

from sweagent import CONFIG_DIR


class BasicCLI:
    def __init__(self, arg_type: type[BaseSettings], default_settings: bool = True):
        self.arg_type = arg_type
        self.default_settings = default_settings

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
        if self.default_settings:
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
        elif self.default_settings and not cli_args.no_config_file:
            config_merged = yaml.safe_load((CONFIG_DIR / "default.yaml").read_text())
        else:
            config_merged = {}

        # args = ScriptArguments.model_validate(config_merged)
        args = CliApp.run(self.arg_type, remaining_args, **config_merged)  # type: ignore
        if cli_args.print_config:  # type: ignore
            print(yaml.dump(args.model_dump()))
            exit(0)
        return args
