import json
import logging
import os
import random
import re
import traceback
from typing import Any, Dict, Tuple
import requests
import yaml

from dataclasses import dataclass
from getpass import getuser
from pathlib import Path
from rich.logging import RichHandler
from simple_parsing import parse
from simple_parsing.helpers import FrozenSerializable, FlattenedAccess
from sweagent import (
    Agent,
    AgentArguments,
    EnvironmentArguments,
    ModelArguments,
    SWEEnv,
    get_data_path_name,
)
from swebench import KEY_INSTANCE_ID, KEY_MODEL, KEY_PREDICTION
from unidiff import PatchSet

from sweagent.environment.utils import is_from_github_url

handler = RichHandler(show_time=False, show_path=False)
handler.setLevel(logging.DEBUG)
logger = logging.getLogger("run_dev")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = False
logging.getLogger("simple_parsing").setLevel(logging.WARNING)


@dataclass(frozen=True)
class ScriptArguments(FlattenedAccess, FrozenSerializable):
    environment: EnvironmentArguments
    agent: AgentArguments
    instance_filter: str = ".*"  # Only run instances that completely match this regex
    skip_existing: bool = True  # Skip instances with existing trajectories
    suffix: str = ""
    open_pr: bool = False  # Open a PR with the patch if we can solve the issue

    @property
    def run_name(self):
        """Generate a unique name for this run based on the arguments."""
        model_name = args.agent.model.model_name.replace(":", "-")
        data_stem = get_data_path_name(args.environment.data_path)
        config_stem = Path(args.agent.config_file).stem

        temp = args.agent.model.temperature
        top_p = args.agent.model.top_p

        per_instance_cost_limit = args.agent.model.per_instance_cost_limit
        install_env = args.environment.install_environment

        return (
            f"{model_name}__{data_stem}__{config_stem}__t-{temp:.2f}__p-{top_p:.2f}"
            + f"__c-{per_instance_cost_limit:.2f}__install-{int(install_env)}"
            + (f"__{self.suffix}" if self.suffix else "")
        )


def main(args: ScriptArguments):
    logger.info(f"📙 Arguments: {args.dumps_yaml()}")
    agent = Agent("primary", args.agent)

    env = SWEEnv(args.environment)

    traj_dir = Path("trajectories") / Path(getuser()) / args.run_name
    os.makedirs(traj_dir, exist_ok=True)

    save_arguments(traj_dir, args)

    for index in range(len(env.data)):
        try:
            # Reset environment
            instance_id = env.data[index]["instance_id"]
            if should_skip(args, traj_dir, instance_id):
                continue
            logger.info("▶️  Beginning task " + str(index))

            observation, info = env.reset(index)
            if info is None:
                continue

            # Get info, patch information
            issue = getattr(env, "query", None)
            files = []
            if "patch" in env.record:
                files = "\n".join(
                    [f"- {x.path}" for x in PatchSet(env.record["patch"]).modified_files]
                )
            # Get test files, F2P tests information
            test_files = []
            if "test_patch" in env.record:
                test_patch_obj = PatchSet(env.record["test_patch"])
                test_files = "\n".join(
                    [f"- {x.path}" for x in test_patch_obj.modified_files + test_patch_obj.added_files]
                )
            tests = ""
            if "FAIL_TO_PASS" in env.record:
                tests = "\n".join([f"- {x}" for x in env.record["FAIL_TO_PASS"]])

            setup_args = {
                "issue": issue,
                "files": files,
                "test_files": test_files,
                "tests": tests
            }
            info = agent.run(
                setup_args=setup_args,
                env=env,
                observation=observation,
                traj_dir=traj_dir,
                return_type="info",
            )
            save_predictions(traj_dir, instance_id, info)
            if should_open_pr(args, info):
                open_pr(env)

        except KeyboardInterrupt:
            logger.info("Exiting InterCode environment...")
            env.close()
            break
        except Exception as e:
            traceback.print_exc()
            logger.warning(f"❌ Failed on {env.record['instance_id']}: {e}")
            env.reset_container()
            continue


def should_open_pr(args, info: Dict[str, Any]) -> bool:
    """Does opening a PR make sense?"""
    if not info.get("submission"):
        logger.info("Not openening PR because submission was made.")
        return False
    if info["exit_status"] != "submitted":
        logger.info("Not openening PR because exit status was %s and not submitted.", info["exit_status"])
        return False
    if not is_from_github_url(args.environment.data_path):
        logger.info("Currently only github is supported to open githubs to. Skipping PR creation.")
        return False
    return True

class GitHubApiException(RuntimeError):
    pass


def get_org_repo_from_gh_url(url: str) -> Tuple[str, str]:
    parse_url = url.removeprefix("https://")
    assert parse_url.startswith("github.com/")
    return tuple(parse_url.split("/")[1:3])  # type: ignore

def get_issue_number_from_gh_url(url: str) -> str:
    return url.split("/")[-1]

def retrieve_issue_title(org: str, repo: str, issue_num: str, token: str) -> str:
    api_url = f"https://api.github.com/repos/{org}/{repo}/issues/{issue_num}"
    response = requests.get(api_url)
    if not response.ok:
        return ""
    issue_data = response.json()
    return issue_data.get('title', '')



def open_pr(env: SWEEnv) -> None:
    """Create a PR with the patch."""
    logger.info("Opening PR")
    # todo: have better way of handling this
    # Adding random string suffix to avoid name conflicts if we had a previously failed run
    branch_name = "swe-agent-patch-branch-" + str(random.random())[2:10]
    print(env.communicate_with_handling(
        input=f"rm model.patch",
        error_msg="Failed to clone repository from mirror",
        timeout_duration=10,
    ))
    print(env.communicate_with_handling(
        input=f"git checkout -b {branch_name}",
        error_msg="Failed to clone repository from mirror",
        timeout_duration=10,
    ))
    print(env.communicate_with_handling(
        input=f"git add .",
        error_msg="Failed to clone repository from mirror",
        timeout_duration=10,
    ))
    print(env.communicate_with_handling(
        input=f"git commit -m 'Solved issue'",
        error_msg="Failed to clone repository from mirror",
        timeout_duration=10,
    ))
    print(env.communicate_with_handling(
        input=f"git push origin {branch_name}",
        error_msg="Failed to clone repository from mirror",
        timeout_duration=10,
    ))
    issue_url = env.args.data_path 
    issue_number = get_issue_number_from_gh_url(issue_url)
    org, repo = get_org_repo_from_gh_url(env.args.data_path)
    issue_title = retrieve_issue_title(org, repo, issue_number, env.token)
    api_url = f"https://api.github.com/repos/{org}/{repo}/pulls"

    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {env.token}',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    # todo: retrieve issue name and add to PR title
    # todo: add representation of trajectory to PR body
    data = {
        'title': f'AI tool PR to fix: {issue_title}',
        'body': f'This is a PR opened by AI tool [SWE Agent](https://github.com/princeton-nlp/SWE-agent/) to close [#{issue_number}]({issue_url}) ({issue_title}).\n\nCloses #{issue_number}.',
        'head': branch_name,
        'base': 'main'
    }
    print("Request data:")
    print(data)
    print(headers)
    print(api_url)
    response = requests.post(api_url, headers=headers, json=data)

    # Raise exception if the response was not successful
    if not response.ok:
        error_message = f"Error {response.status_code}: {response.text}"
        if response.status_code == 403:
            raise GitHubApiException("Forbidden: " + error_message)
        else:
            raise GitHubApiException(error_message)

    print("Success:", response.json())


def save_arguments(traj_dir, args):
    """Save the arguments to a yaml file to the run's trajectory directory."""
    log_path = traj_dir / "args.yaml"

    if log_path.exists():
        try:
            other_args = args.load_yaml(log_path)
            if (args.dumps_yaml() != other_args.dumps_yaml()):  # check yaml equality instead of object equality
                logger.warning("**************************************************")
                logger.warning("Found existing args.yaml with different arguments!")
                logger.warning("**************************************************")
        except Exception as e:
            logger.warning(f"Failed to load existing args.yaml: {e}")

    with log_path.open("w") as f:
        args.dump_yaml(f)


def should_skip(args, traj_dir, instance_id):
    """Check if we should skip this instance based on the instance filter and skip_existing flag."""
    # Skip instances that don't match the instance filter
    if re.match(args.instance_filter, instance_id) is None:
        logger.info(f"Instance filter not matched. Skipping instance {instance_id}")
        return True

    # If flag is set to False, don't skip
    if not args.skip_existing:
        return False

    # Check if there's an existing trajectory for this instance
    log_path = traj_dir / (instance_id + ".traj")
    if log_path.exists():
        with log_path.open("r") as f:
            data = json.load(f)
        # If the trajectory has no exit status, it's incomplete and we will redo it
        exit_status = data["info"].get("exit_status", None)
        if exit_status == "early_exit" or exit_status is None:
            logger.info(f"Found existing trajectory with no exit status: {log_path}")
            logger.info("Removing incomplete trajectory...")
            os.remove(log_path)
        else:
            logger.info(f"⏭️ Skipping existing trajectory: {log_path}")
            return True
    return False


def save_predictions(traj_dir, instance_id, info):
    output_file = Path(traj_dir) / "all_preds.jsonl"
    model_patch = info["submission"] if "submission" in info else None
    datum = {
        KEY_MODEL: Path(traj_dir).name,
        KEY_INSTANCE_ID: instance_id,
        KEY_PREDICTION: model_patch,
    }
    with open(output_file, "a+") as fp:
        print(json.dumps(datum), file=fp, flush=True)
    logger.info(f"Saved predictions to {output_file}")


if __name__ == "__main__":
    defaults = ScriptArguments(
        suffix="",
        environment=EnvironmentArguments(
            image_name="swe-agent",
            data_path="princeton-nlp/SWE-bench_Lite",
            split="dev",
            verbose=True,
            install_environment=True,
        ),
        skip_existing=True,
        agent=AgentArguments(
            model=ModelArguments(
                model_name="gpt4",
                total_cost_limit=0.0,
                per_instance_cost_limit=2.0,
                temperature=0.2,
                top_p=0.95,
            ),
            config_file="config/default.yaml",
        ),
    )

    # Nicer yaml dumping of multiline strings
    def multiline_representer(dumper, data):
        """configures yaml for dumping multiline strings
        Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
        """
        if data.count("\n") > 0:  # check for multiline string
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(str, multiline_representer)

    args = parse(ScriptArguments, default=defaults, add_config_path_arg=False)
    main(args)
