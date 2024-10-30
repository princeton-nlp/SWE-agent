from __future__ import annotations

# try:
#     import rich
# except ModuleNotFoundError as e:
#     msg = (
#         "You probably either forgot to install the dependencies "
#         "or forgot to activate your conda or virtual environment."
#     )
#     raise RuntimeError(msg) from e
import json
import logging
import re
import traceback
from argparse import ArgumentParser
from pprint import pprint

from sweagent.environment.config.deployment import DockerDeploymentConfig
from sweagent.run.hooks.abstract import RunHook
from sweagent.run.run_single import RunSingleActionConfig
from sweagent.utils.log import add_file_handler, get_logger

try:
    from rich_argparse import RichHelpFormatter
except ImportError:
    msg = "Please install the rich_argparse package with `pip install rich_argparse`."
    raise ImportError(msg)
import datetime
from getpass import getuser
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, CliApp
from rich.markdown import Markdown
from swebench.harness.constants import KEY_INSTANCE_ID, KEY_MODEL, KEY_PREDICTION
from unidiff import PatchSet

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentInstanceConfig, SWEEnv

__doc__: str = """ Run inference. Usage examples:

```bash
# Run over a github issue:
python run.py --model_name "gpt4" --data_path "https://github.com/pvlib/pvlib-python/issues/1603" --config_file "config/default_from_url.yaml"
# Apply a patch in a local repository to an issue specified as Markdown file and run a custom installer script in the container
python run.py --model_name "gpt4" --data_path "/path/to/my_issue.md" --repo_path "/path/to/my/local/repo" --environment_setup "/path/to/setup.sh" --config_file "config/default_from_url.yaml" --apply_patch_locally
```

**For more information**: https://princeton-nlp.github.io/SWE-agent/usage/cl_tutorial/
"""


logger = get_logger("swe-agent-run")
logging.getLogger("simple_parsing").setLevel(logging.WARNING)


class ScriptArguments(BaseSettings):
    """Configure the control flow of the run.py script"""

    environment: EnvironmentInstanceConfig = Field(..., default_factory=EnvironmentInstanceConfig)
    agent: AgentConfig = Field(..., default_factory=AgentConfig)
    actions: RunSingleActionConfig = Field(..., default_factory=RunSingleActionConfig)
    # Only run instances that completely match this regex
    instance_filter: str = ".*"
    # Skip instances with existing trajectories
    skip_existing: bool = True
    # Suffix for the run name (used for example in trajectory directory naming)
    suffix: str = ""
    # Raise unhandled exceptions during the run (useful for debugging)
    raise_exceptions: bool = False
    # Dump the entire config to the log
    print_config: bool = True
    # Run the agent in CTF mode (SWE-agent: EnIGMA)
    ctf: bool = False

    run_name: str = ""

    def model_post_init(self, __context):
        if not self.run_name:
            self.run_name = self._generate_run_name()

    def _generate_run_name(self) -> str:
        """Generate a unique name for this run based on the arguments."""
        model_name = self.agent.model.name.replace(":", "-")
        # todo: Need to set this properly
        data_stem = "todo"  # get_data_path_name(self.environment.data_path)
        # assert self.agent.config_file is not None  # mypy
        # config_stem = Path(self.agent.config_file).stem

        temp = self.agent.model.temperature
        top_p = self.agent.model.top_p

        per_instance_cost_limit = self.agent.model.per_instance_cost_limit
        # install_env = self.environment.install_environment

        return (
            f"{model_name}__{data_stem}__t-{temp:.2f}__p-{top_p:.2f}"
            + f"__c-{per_instance_cost_limit:.2f}"
            + (f"__{self.suffix}" if self.suffix else "")
        )


class _ContinueLoop(Exception):
    """Used for internal control flow"""


class Main:
    def __init__(self, args: ScriptArguments):
        self.traj_dir = Path("trajectories") / Path(getuser()) / args.run_name
        self.traj_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        log_path = self.traj_dir / f"run-{timestamp}.log"
        logger.info("Logging to %s", log_path)
        add_file_handler(log_path)
        if args.print_config:
            dump = yaml.dump(args.model_dump())
            logger.info(f"📙 Arguments: {dump}")
        self.args = args
        self.agent = Agent("primary", args.agent)
        self.env = SWEEnv(args.environment)
        self._save_arguments()
        default_hooks = [
            # SaveApplyPatchHook(),
            # OpenPRHook(),
        ]
        self.hooks: list[RunHook] = []
        for hook in default_hooks:
            self.add_hook(hook)

    def add_hook(self, hook: RunHook):
        hook.on_init(args=self.args, agent=self.agent, env=self.env, traj_dir=self.traj_dir)
        self.hooks.append(hook)

    def run(self, index: int) -> None:
        # Reset environment
        instance_id = self.env.data[index]["instance_id"]
        for hook in self.hooks:
            hook.on_instance_start(index=index, instance=self.env.data[index])
        assert isinstance(instance_id, str)  # mypy
        if self.should_skip(instance_id):
            for hook in self.hooks:
                hook.on_instance_skipped()
            raise _ContinueLoop
        logger.info("▶️  Beginning task " + str(index))

        observation, info = self.env.reset(index)
        if info is None:
            raise _ContinueLoop

        # Get info, patch information
        issue = getattr(self.env, "query", None)
        files = []
        assert self.env.record is not None  # mypy
        if "patch" in self.env.record:
            files = "\n".join([f"- {x.path}" for x in PatchSet(self.env.record["patch"]).modified_files])
        # Get test files, F2P tests information
        test_files = []
        if "test_patch" in self.env.record:
            test_patch_obj = PatchSet(self.env.record["test_patch"])
            test_files = "\n".join([f"- {x.path}" for x in test_patch_obj.modified_files + test_patch_obj.added_files])
        tests = ""
        if "FAIL_endTO_PASS" in self.env.record:
            tests = "\n".join([f"- {x}" for x in self.env.record["FAIL_TO_PASS"]])

        setup_args = {"issue": issue, "files": files, "test_files": test_files, "tests": tests}
        # challenge = self.env.challenge
        # if challenge is not None:
        #     setup_args["flag_format"] = extract_flag_format(challenge["flag"])
        #     setup_args["name"] = challenge["name"]
        #     setup_args["description"] = challenge["description"]
        #     setup_args["category_friendly"] = challenge["category_friendly"]
        #     setup_args["points"] = challenge["points"]
        #     setup_args["files"] = challenge["files"] or "No files included in this challenge."
        #     setup_args["box"] = challenge.get("server_name")
        #     setup_args["port"] = challenge.get("port")
        #     setup_args["server_description"] = challenge.get("server_description")
        info, trajectory = self.agent.run(
            setup_args=setup_args,
            env=self.env,
            observation=observation,
            traj_dir=self.traj_dir,
            return_type="info_trajectory",
        )
        challenge = None
        self._save_predictions(instance_id, info, challenge)
        for hook in self.hooks:
            hook.on_instance_completed(info=info, trajectory=trajectory)

    def main(self):
        for hook in self.hooks:
            hook.on_start()
        for index in range(len(self.env.data)):
            try:
                self.run(index)
            except _ContinueLoop:
                continue
            except KeyboardInterrupt:
                logger.info("Exiting InterCode environment...")
                self.env.close()
                break
            except SystemExit:
                logger.critical("❌ Exiting because SystemExit was called")
                self.env.close()
                logger.info("Container closed")
                raise
            except Exception as e:
                logger.warning(traceback.format_exc())
                if self.args.raise_exceptions:
                    self.env.close()
                    raise e
                if self.env.record:
                    logger.warning(f"❌ Failed on {self.env.record['instance_id']}: {e}")
                else:
                    logger.warning("❌ Failed on unknown instance")
                self.env.reset_container()
                continue
        self.env.close()
        for hook in self.hooks:
            hook.on_end()

    def _save_arguments(self) -> None:
        """Save the arguments to a yaml file to the run's trajectory directory."""
        log_path = self.traj_dir / "args.yaml"

        if log_path.exists():
            try:
                other_args = ScriptArguments.model_validate(yaml.safe_load(log_path.read_text()))
                if other_args != self.args:
                    logger.warning("**************************************************")
                    logger.warning("Found existing args.yaml with different arguments!")
                    logger.warning("**************************************************")
            except Exception:
                logger.warning(f"Failed to load existing args.yaml: {traceback.format_exc()}")

        log_path.write_text(yaml.dump(self.args.model_dump()))

    def should_skip(self, instance_id: str) -> bool:
        """Check if we should skip this instance based on the instance filter and skip_existing flag."""
        # Skip instances that don't match the instance filter
        if re.match(self.args.instance_filter, instance_id) is None:
            logger.info(f"⏭️ Instance filter not matched. Skipping instance {instance_id}")
            return True

        # If flag is set to False, don't skip
        if not self.args.skip_existing:
            return False

        # Check if there's an existing trajectory for this instance
        log_path = self.traj_dir / (instance_id + ".traj")
        if not log_path.exists():
            return False

        content = log_path.read_text()
        if not content.strip():
            logger.warning("Found empty trajectory: %s. Removing.", log_path)
            log_path.unlink()
            return False

        data = json.loads(content)
        # If the trajectory has no exit status, it's incomplete and we will redo it
        exit_status = data["info"].get("exit_status", None)
        if exit_status == "early_exit" or exit_status is None:
            logger.warning(f"Found existing trajectory with no exit status: {log_path}. Removing.")
            log_path.unlink()
            return False

        logger.info(f"⏭️ Skipping existing trajectory: {log_path}")
        return True

    def _save_predictions(self, instance_id: str, info, challenge: dict[str, str] | None):
        output_file = self.traj_dir / "all_preds.jsonl"
        model_patch = info["submission"] if "submission" in info else None
        datum = {
            KEY_MODEL: Path(self.traj_dir).name,
            KEY_INSTANCE_ID: instance_id,
            KEY_PREDICTION: model_patch,
        }
        # if challenge is not None:
        #     challenge_datum = {
        #         "challenge_name": challenge["name"],
        #         "challenge_category": challenge["category"],
        #         "challenge_path": challenge["file_path"],
        #     }
        #     datum.update(challenge_datum)
        with open(output_file, "a+") as fp:
            print(json.dumps(datum), file=fp, flush=True)
        logger.info(f"Saved predictions to {output_file}")


def get_args(args=None) -> ScriptArguments:
    """Parse command line arguments and return a ScriptArguments object.

    Args:
        args: Optional list of arguments to parse. If not provided, uses sys.argv.
    """
    # The defaults if no config file is provided
    # Otherwise, the configs from the respective classes will be used
    no_config_defaults = ScriptArguments(
        suffix="",
        environment=EnvironmentInstanceConfig(
            deployment=DockerDeploymentConfig(),
            # data_path="princeton-nlp/SWE-bench_Lite",
            # split="dev",
            # verbose=True,
            # install_environment=True,
        ),
        skip_existing=True,
        agent=AgentConfig(
            system_template="",
            instance_template="",
            model=ModelArguments(
                name="gpt4",
                total_cost_limit=0.0,
                per_instance_cost_limit=3.0,
                temperature=0.0,
                top_p=0.95,
            ),
        ),
        actions=RunSingleActionConfig(open_pr=False, skip_if_commits_reference_issue=True),
        ctf=False,
    )

    parser = ArgumentParser(
        description=Markdown(__doc__),
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--config", type=str, action="append", default=[])

    args, remaining_args = parser.parse_known_args(args)

    config_merged = {}
    if args.config:
        for _f in args.config:
            _loaded = yaml.safe_load(Path(_f).read_text())
            config_merged.update(_loaded)
    else:
        config_merged = no_config_defaults.model_dump()

    # args = ScriptArguments.model_validate(config_merged)
    print("Config merged")
    pprint(config_merged)
    args = ScriptArguments.model_validate(config_merged)
    return CliApp.run(ScriptArguments, remaining_args, **config_merged)
    # args = CliApp.run(ScriptArguments, remaining_args, model_init_data=config_merged)

    # todo: Do we need this?
    # Nicer yaml dumping of multiline strings
    # def multiline_representer(dumper, data):
    #     """configures yaml for dumping multiline strings
    #     Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
    #     """
    #     if data.count("\n") > 0:  # check for multiline string
    #         return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    #     return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    # yaml.add_representer(str, multiline_representer)


def main(args: ScriptArguments):
    Main(args).main()


if __name__ == "__main__":
    main(get_args())
