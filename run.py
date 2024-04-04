import json
import logging
import os
import re
import traceback
from pathlib import Path
import typer
import yaml
from rich.logging import RichHandler
from sweagent import (
    Agent,
    AgentArguments,
    EnvironmentArguments,
    ModelArguments,
    SWEEnv,
    get_data_path_name,
)
from swebench import KEY_INSTANCE_ID, KEY_MODEL, KEY_PREDICTION
from typing import Dict, Any, Optional
from getpass import getuser
from unidiff import PatchSet


app = typer.Typer()

handler = RichHandler(show_time=False, show_path=False)
handler.setLevel(logging.DEBUG)
logger = logging.getLogger("run_dev")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = False
logging.getLogger("simple_parsing").setLevel(logging.WARNING)


def get_run_name(args: Dict[str, Any]) -> str:
    """Generate a unique name for this run based on the arguments."""
    model_name = args["agent"]["model"]["model_name"].replace(":", "-")
    data_stem = get_data_path_name(args["environment"]["data_path"])
    config_stem = Path(args["agent"]["config_file"]).stem

    temp = args["agent"]["model"]["temperature"]
    top_p = args["agent"]["model"]["top_p"]
    per_instance_cost_limit = args["agent"]["model"]["per_instance_cost_limit"]
    install_env = args["environment"]["install_environment"]

    suffix = args.get("suffix", "")
    return f"{model_name}__{data_stem}__{config_stem}__t-{temp:.2f}__p-{top_p:.2f}__c-{per_instance_cost_limit:.2f}__install-{int(install_env)}{f'__{suffix}' if suffix else ''}"


def save_arguments(traj_dir: Path, args: Dict[str, Any]):
    log_path = traj_dir / "args.yaml"
    if log_path.exists():
        with open(log_path, "r") as f:
            existing_args = yaml.safe_load(f)
            if args != existing_args:
                logger.warning("Found existing args.yaml with different arguments!")
    with open(log_path, "w") as f:
        yaml.safe_dump(args, f)


def should_skip(args: Dict[str, Any], traj_dir: Path, instance_id: str) -> bool:
    if not re.match(args["instance_filter"], instance_id):
        logger.info(f"Instance filter not matched. Skipping instance {instance_id}")
        return True
    if not args["skip_existing"]:
        return False
    log_path = traj_dir / (instance_id + ".traj")
    if log_path.exists():
        with open(log_path, "r") as f:
            data = json.load(f)
        exit_status = data["info"].get("exit_status", None)
        if exit_status in [None, "early_exit"]:
            logger.info(f"Removing incomplete trajectory: {log_path}")
            os.remove(log_path)
        else:
            logger.info(f"Skipping existing trajectory: {log_path}")
            return True
    return False


def save_predictions(traj_dir: Path, instance_id: str, info: Dict[str, Any]):
    output_file = traj_dir / "all_preds.jsonl"
    model_patch = info.get("submission", None)
    datum = {
        KEY_MODEL: traj_dir.name,
        KEY_INSTANCE_ID: instance_id,
        KEY_PREDICTION: model_patch,
    }
    with open(output_file, "a") as fp:
        print(json.dumps(datum), file=fp)


@app.command()
def main(
    environment_image_name: str = typer.Option(
        ..., "--env-img", help="Environment image name"
    ),
    data_path: str = typer.Option(..., "--data-path", help="Data path"),
    split: str = typer.Option("dev", "--split", help="Data split"),
    verbose: bool = typer.Option(True, "--verbose", help="Verbose output"),
    install_environment: bool = typer.Option(
        True, "--install-env", help="Install environment flag"
    ),
    model_name: str = typer.Option(..., "--model-name", help="Model name"),
    total_cost_limit: float = typer.Option(
        0.0, "--total-cost", help="Total cost limit"
    ),
    per_instance_cost_limit: float = typer.Option(
        2.0, "--per-instance-cost", help="Per instance cost limit"
    ),
    temperature: float = typer.Option(0.2, "--temp", help="Temperature for generation"),
    top_p: float = typer.Option(0.95, "--top-p", help="Top P for generation"),
    config_file: Path = typer.Option(
        ..., "--config", help="Path to the configuration file"
    ),
    instance_filter: str = typer.Option(
        ".*", "--instance-filter", help="Regex filter for instance IDs"
    ),
    skip_existing: bool = typer.Option(
        True, "--skip-existing", help="Skip existing trajectories"
    ),
    suffix: Optional[str] = typer.Option(
        None, "--suffix", help="Suffix for the run name"
    ),
):
    # Convert command line arguments to ScriptArguments-like structure
    environment_args = EnvironmentArguments(
        image_name=environment_image_name,
        data_path=data_path,
        split=split,
        verbose=verbose,
        install_environment=install_environment,
    )
    model_args = ModelArguments(
        model_name=model_name,
        total_cost_limit=total_cost_limit,
        per_instance_cost_limit=per_instance_cost_limit,
        temperature=temperature,
        top_p=top_p,
    )
    agent_args = AgentArguments(model=model_args, config_file=config_file)
    script_args = {
        "environment": environment_args,
        "agent": agent_args,
        "instance_filter": instance_filter,
        "skip_existing": skip_existing,
        "suffix": suffix,
    }

    logger.info(f"📙 Arguments: {yaml.safe_dump(script_args)}")
    agent = Agent("primary", AgentArguments(**script_args["agent"]))
    env = SWEEnv(EnvironmentArguments(**script_args["environment"]))

    traj_dir = Path("trajectories") / getuser() / get_run_name(script_args)
    os.makedirs(traj_dir, exist_ok=True)
    save_arguments(traj_dir, script_args)

    for index, instance in enumerate(env.data):
        try:
            instance_id = instance["instance_id"]
            if should_skip(script_args, traj_dir, instance_id):
                continue
            logger.info(f"▶️ Beginning task {index}")

            observation, info = env.reset(index)
            if info is None:
                continue

            # Extracting issue information
            issue = getattr(env, "query", None)
            files = []
            if "patch" in env.record:
                files = "\n".join([f"- {x.path}" for x in PatchSet(env.record["patch"]).modified_files])

            # Extracting test file modifications and additions
            test_files = []
            if "test_patch" in env.record:
                test_patch_obj = PatchSet(env.record["test_patch"])
                test_files = "\n".join([f"- {x.path}" for x in test_patch_obj.modified_files + test_patch_obj.added_files])

            # Extracting tests that changed from fail to pass
            tests = ""
            if "FAIL_TO_PASS" in env.record:
                tests = "\n".join([f"- {x}" for x in env.record["FAIL_TO_PASS"]])

            setup_args = {
                "issue": issue,
                "files": files,
                "test_files": test_files,
                "tests": tests,
            }

            # Running the agent with the collected setup arguments
            info = agent.run(
                setup_args=setup_args,
                env=env,
                observation=observation,
                traj_dir=traj_dir,
                return_type="info",
            )

            # Saving the predictions
            save_predictions(traj_dir, instance_id, info)

        except KeyboardInterrupt:
            logger.info("Exiting...")
            break
        except Exception as e:
            traceback.print_exc()
            logger.warning(f"❌ Failed on {instance["instance_id"]}: {e}")
            continue


if __name__ == "__main__":
    app()
