from __future__ import annotations

import logging
from argparse import ArgumentParser

from omegaconf import OmegaConf

from sweagent.utils.log import add_file_handler, get_logger

try:
    import rich
except ModuleNotFoundError as e:
    msg = (
        "You probably either forgot to install the dependencies "
        "or forgot to activate your conda or virtual environment."
    )
    raise RuntimeError(msg) from e
import json
import re
import subprocess
import traceback
from typing import Any

import rich.console
import rich.markdown
import rich.panel

try:
    from rich_argparse import RichHelpFormatter
except ImportError:
    msg = "Please install the rich_argparse package with `pip install rich_argparse`."
    raise ImportError(msg)
import datetime
from dataclasses import dataclass
from getpass import getuser
from pathlib import Path

import yaml
from rich.markdown import Markdown
from swebench.harness.constants import KEY_INSTANCE_ID, KEY_MODEL, KEY_PREDICTION
from unidiff import PatchSet

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import DeploymentConfig, EnvironmentArguments, SWEEnv
from sweagent.environment.utils import (
    InvalidGithubURL,
    extract_flag_format,
    get_associated_commit_urls,
    get_data_path_name,
    get_gh_issue_data,
    parse_gh_issue_url,
)

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


@dataclass
class ActionsArguments:
    """Run real-life actions (opening PRs, etc.) if we can solve the issue."""

    # Open a PR with the patch if we can solve the issue
    open_pr: bool = False
    # When working with local repository: Apply patch
    apply_patch_locally: bool = False
    # Option to be used with open_pr: Skip action if there are already commits claiming
    # to fix the issue. Please only set this to False if you are sure the commits are
    # not fixes or if this is your own repository!
    skip_if_commits_reference_issue: bool = True
    # OBSOLETE. Do not use, will raise error. Please specify --repo_path instead.
    push_gh_repo_url: str = ""

    def __post_init__(self):
        if self.push_gh_repo_url:
            msg = "push_gh_repo_url is obsolete. Use repo_path instead"
            raise ValueError(msg)


@dataclass
class ScriptArguments:
    """Configure the control flow of the run.py script"""

    environment: EnvironmentArguments
    agent: AgentConfig
    actions: ActionsArguments
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

    def __post_init__(self):
        if not self.run_name:
            self.run_name = self._generate_run_name()

    def _generate_run_name(self) -> str:
        """Generate a unique name for this run based on the arguments."""
        model_name = self.agent.model.model_name.replace(":", "-")
        data_stem = get_data_path_name(self.environment.data_path)
        # assert self.agent.config_file is not None  # mypy
        # config_stem = Path(self.agent.config_file).stem

        temp = self.agent.model.temperature
        top_p = self.agent.model.top_p

        per_instance_cost_limit = self.agent.model.per_instance_cost_limit
        install_env = self.environment.install_environment

        return (
            f"{model_name}__{data_stem}__t-{temp:.2f}__p-{top_p:.2f}"
            + f"__c-{per_instance_cost_limit:.2f}__install-{int(install_env)}"
            + (f"__{self.suffix}" if self.suffix else "")
        )


class _ContinueLoop(Exception):
    """Used for internal control flow"""


class MainHook:
    """Hook structure for the web server or other addons to interface with"""

    @staticmethod
    def _is_promising_patch(info: dict[str, Any]) -> bool:
        """Do we actually believe that the patch will solve the issue?
        Or are we just submitting the last patch we generated before hitting an error?
        """
        # The exit status can also be `submitted (exit_cost)` etc.
        return info["exit_status"] == "submitted" and info.get("submission") is not None

    def on_init(self, *, args: ScriptArguments, agent: Agent, env: SWEEnv, traj_dir: Path):
        """Called when hook is initialized"""

    def on_start(self):
        """Called at the beginning of `Main.main`"""

    def on_end(self):
        """Called at the end of `Main.main`"""

    def on_instance_start(self, *, index: int, instance: dict[str, Any]):
        """Called at the beginning of each instance loop in `Main.run`"""

    def on_instance_skipped(
        self,
    ):
        """Called when an instance is skipped in `Main.run`"""

    def on_instance_completed(self, *, info, trajectory):
        """Called when an instance is completed in `Main.run`"""


class SaveApplyPatchHook(MainHook):
    """This hook saves patches to a separate directory and optionally applies them to a local repository."""

    def on_init(self, *, args: ScriptArguments, agent: Agent, env: SWEEnv, traj_dir: Path):
        self._traj_dir = traj_dir
        self._apply_patch_locally = args.actions.apply_patch_locally
        self._instance = None

    def on_instance_start(self, *, index: int, instance: dict[str, Any]):
        self._instance = instance

    def on_instance_completed(self, *, info, trajectory):
        assert self._instance is not None  # mypy
        instance_id = self._instance["instance_id"]
        patch_path = self._save_patch(instance_id, info)
        if patch_path:
            if not self._apply_patch_locally:
                return
            if not self._is_promising_patch(info):
                return
            assert self._instance  # mypy
            if self._instance["repo_type"] != "local":
                return
            local_dir = Path(self._instance["repo"])
            self._apply_patch(patch_path, local_dir)

    @staticmethod
    def _print_patch_message(patch_output_file: Path):
        console = rich.console.Console()
        msg = [
            "SWE-agent has produced a patch that it believes will solve the issue you submitted!",
            "Use the code snippet below to inspect or apply it!",
        ]
        panel = rich.panel.Panel.fit(
            "\n".join(msg),
            title="🎉 Submission successful 🎉",
        )
        console.print(panel)
        content = [
            "```bash",
            "# The patch has been saved to your local filesystem at:",
            f"PATCH_FILE_PATH='{patch_output_file.resolve()}'",
            "# Inspect it:",
            'cat "${PATCH_FILE_PATH}"',
            "# Apply it to a local repository:",
            "cd <your local repo root>",
            'git apply "${PATCH_FILE_PATH}"',
            "```",
        ]
        console.print(rich.markdown.Markdown("\n".join(content)))

    def _save_patch(self, instance_id: str, info) -> Path | None:
        """Create patch files that can be applied with `git am`.

        Returns:
            The path to the patch file, if it was saved. Otherwise, returns None.
        """
        patch_output_dir = self._traj_dir / "patches"
        patch_output_dir.mkdir(exist_ok=True, parents=True)
        patch_output_file = patch_output_dir / f"{instance_id}.patch"
        if info.get("submission") is None:
            logger.info("No patch to save.")
            return None
        model_patch = info["submission"]
        patch_output_file.write_text(model_patch)
        if self._is_promising_patch(info):
            # Only print big congratulations if we actually believe
            # the patch will solve the issue
            self._print_patch_message(patch_output_file)
        return patch_output_file

    def _apply_patch(self, patch_file: Path, local_dir: Path) -> None:
        """Apply a patch to a local directory."""

        assert local_dir.is_dir()
        assert patch_file.exists()
        # The resolve() is important, because we're gonna run the cmd
        # somewhere else
        cmd = ["git", "apply", str(patch_file.resolve())]
        try:
            subprocess.run(cmd, cwd=local_dir, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch {patch_file} to {local_dir}: {e}")
            return
        logger.info(f"Applied patch {patch_file} to {local_dir}")


class OpenPRHook(MainHook):
    """This hook opens a PR if the issue is solved and the user has enabled the option."""

    def on_init(self, *, args: ScriptArguments, agent: Agent, env: SWEEnv, traj_dir: Path):
        self._env = env
        self._token: str = env._github_token
        self._data_path = args.environment.data_path
        self._open_pr = args.actions.open_pr
        self._skip_if_commits_reference_issue = args.actions.skip_if_commits_reference_issue

    def on_instance_completed(self, *, info, trajectory):
        if self._open_pr and self.should_open_pr(info):
            self._env.open_pr(trajectory=trajectory)

    def should_open_pr(self, info: dict[str, Any]) -> bool:
        """Does opening a PR make sense?"""
        if not info.get("submission"):
            logger.info("Not opening PR because no submission was made.")
            return False
        if info["exit_status"] != "submitted":
            logger.info("Not opening PR because exit status was %s and not submitted.", info["exit_status"])
            return False
        try:
            issue = get_gh_issue_data(self._data_path, token=self._token)
        except InvalidGithubURL:
            logger.info("Currently only GitHub is supported to open PRs to. Skipping PR creation.")
            return False
        if issue.state != "open":
            logger.info(f"Issue is not open (state={issue.state}. Skipping PR creation.")
            return False
        if issue.assignee:
            logger.info("Issue is already assigned. Skipping PR creation. Be nice :)")
            return False
        if issue.locked:
            logger.info("Issue is locked. Skipping PR creation.")
            return False
        org, repo, issue_number = parse_gh_issue_url(self._data_path)
        associated_commits = get_associated_commit_urls(org, repo, issue_number, token=self._token)
        if associated_commits:
            commit_url_strs = ", ".join(associated_commits)
            if self._skip_if_commits_reference_issue:
                logger.info(f"Issue already has associated commits (see {commit_url_strs}). Skipping PR creation.")
                return False
            else:
                logger.warning(
                    "Proceeding with PR creation even though there are already commits "
                    f"({commit_url_strs}) associated with the issue. Please only do this for your own repositories "
                    "or after verifying that the existing commits do not fix the issue.",
                )
        return True


class Main:
    def __init__(self, args: ScriptArguments):
        self.traj_dir = Path("trajectories") / Path(getuser()) / args.run_name
        self.traj_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        log_path = self.traj_dir / f"run-{timestamp}.log"
        logger.info("Logging to %s", log_path)
        add_file_handler(log_path)
        if args.print_config:
            dump = OmegaConf.to_yaml(args)
            logger.info(f"📙 Arguments: {dump}")
        self.args = args
        self.agent = Agent("primary", args.agent)
        self.env = SWEEnv(args.environment)
        self._save_arguments()
        default_hooks = [
            SaveApplyPatchHook(),
            OpenPRHook(),
        ]
        self.hooks: list[MainHook] = []
        for hook in default_hooks:
            self.add_hook(hook)

    def add_hook(self, hook: MainHook):
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
        challenge = self.env.challenge
        if challenge is not None:
            setup_args["flag_format"] = extract_flag_format(challenge["flag"])
            setup_args["name"] = challenge["name"]
            setup_args["description"] = challenge["description"]
            setup_args["category_friendly"] = challenge["category_friendly"]
            setup_args["points"] = challenge["points"]
            setup_args["files"] = challenge["files"] or "No files included in this challenge."
            setup_args["box"] = challenge.get("server_name")
            setup_args["port"] = challenge.get("port")
            setup_args["server_description"] = challenge.get("server_description")
        info, trajectory = self.agent.run(
            setup_args=setup_args,
            env=self.env,
            observation=observation,
            traj_dir=self.traj_dir,
            return_type="info_trajectory",
        )
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
                other_args = OmegaConf.load(log_path)
                if OmegaConf.to_yaml(self.args) != OmegaConf.to_yaml(
                    other_args
                ):  # check yaml equality instead of object equality
                    logger.warning("**************************************************")
                    logger.warning("Found existing args.yaml with different arguments!")
                    logger.warning("**************************************************")
            except Exception:
                logger.warning(f"Failed to load existing args.yaml: {traceback.format_exc()}")

        log_path.write_text(OmegaConf.to_yaml(self.args))

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
        if challenge is not None:
            challenge_datum = {
                "challenge_name": challenge["name"],
                "challenge_category": challenge["category"],
                "challenge_path": challenge["file_path"],
            }
            datum.update(challenge_datum)
        with open(output_file, "a+") as fp:
            print(json.dumps(datum), file=fp, flush=True)
        logger.info(f"Saved predictions to {output_file}")


def get_args(args=None) -> ScriptArguments:
    """Parse command line arguments and return a ScriptArguments object.

    Args:
        args: Optional list of arguments to parse. If not provided, uses sys.argv.
    """
    defaults = ScriptArguments(
        suffix="",
        environment=EnvironmentArguments(
            deployment=DeploymentConfig(),
            data_path="princeton-nlp/SWE-bench_Lite",
            split="dev",
            verbose=True,
            install_environment=True,
        ),
        skip_existing=True,
        agent=AgentConfig(
            system_template="",
            instance_template="",
            model=ModelArguments(
                model_name="gpt4",
                total_cost_limit=0.0,
                per_instance_cost_limit=3.0,
                temperature=0.0,
                top_p=0.95,
            ),
        ),
        actions=ActionsArguments(open_pr=False, skip_if_commits_reference_issue=True),
        ctf=False,
    )

    default_config = OmegaConf.structured(defaults)

    parser = ArgumentParser(
        description=Markdown(__doc__),
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--config", type=str, action="append", default=[])
    parser.add_argument("overrides", nargs="*")

    args = parser.parse_args(args)

    cfg_files = [OmegaConf.load(f) for f in args.config]

    for _f in cfg_files:
        print(OmegaConf.to_yaml(_f))

    overrides = OmegaConf.from_dotlist(args.overrides)

    cfg = OmegaConf.merge(default_config, *cfg_files, overrides)

    # todo: Do we need this?
    # Nicer yaml dumping of multiline strings
    def multiline_representer(dumper, data):
        """configures yaml for dumping multiline strings
        Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
        """
        if data.count("\n") > 0:  # check for multiline string
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(str, multiline_representer)

    return cfg  # type: ignore


def main(args: ScriptArguments):
    Main(args).main()


if __name__ == "__main__":
    main(get_args())
