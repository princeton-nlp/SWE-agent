from __future__ import annotations

import dataclasses
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

import docker
from run import ActionsArguments, Main, MainHook, OpenPRHook, ScriptArguments
from sweagent.agent.agents import Agent, AgentArguments, AgentHook
from sweagent.agent.models import ModelArguments
from sweagent.environment.swe_env import EnvironmentArguments, SWEEnv


@pytest.mark.slow()
def test_run_cli_help():
    args = [
        "python",
        "run.py",
        "--help",
    ]
    subprocess.run(args, check=True)


@pytest.fixture()
def open_pr_hook_init_for_sop():
    hook = OpenPRHook()
    hook._token = os.environ.get("GITHUB_TOKEN", "")
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/1"
    hook._open_pr = True
    hook._skip_if_commits_reference_issue = True
    return hook


@pytest.fixture()
def info_dict():
    return {
        "submission": "asdf",
        "exit_status": "submitted",
    }


def test_should_open_pr_fail_submission(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    info_dict["submission"] = None
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_exit(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    info_dict["exit_status"] = "fail"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_invalid_url(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "asdf"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_closed(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/16"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_assigned(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/17"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_locked(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/18"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_has_pr(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/19"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_success_has_pr_override(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/19"
    hook._skip_if_commits_reference_issue = False
    assert hook.should_open_pr(info_dict)


class RaisesExceptionHook(MainHook):
    def on_instance_start(self, *, index: int, instance: dict[str, Any]):
        msg = "test exception"
        raise ValueError(msg)


@pytest.fixture()
def test_script_args():
    return ScriptArguments(
        suffix="",
        environment=EnvironmentArguments(
            image_name="sweagent/swe-agent:latest",
            data_path="https://github.com/klieret/swe-agent-test-repo/issues/1",
            split="dev",
            verbose=True,
            install_environment=True,
        ),
        skip_existing=False,
        agent=AgentArguments(
            model=ModelArguments(
                model_name="instant_empty_submit",
                total_cost_limit=0.0,
                per_instance_cost_limit=3.0,
                temperature=0.0,
                top_p=0.95,
            ),
            config_file=Path("config/default.yaml"),
        ),
        actions=ActionsArguments(open_pr=False, skip_if_commits_reference_issue=True),
        raise_exceptions=True,
        print_config=False,
    )


@pytest.mark.slow()
def test_exception_raised(test_script_args: ScriptArguments):
    assert test_script_args.raise_exceptions
    main = Main(test_script_args)
    main.add_hook(RaisesExceptionHook())
    with pytest.raises(ValueError, match="test exception"):
        main.main()


@pytest.mark.slow()
class CreateFakeLogFile(MainHook):
    """Testing the skip functionality"""

    def on_init(self, *, args: ScriptArguments, agent: Agent, env: SWEEnv, traj_dir: Path):
        self._traj_dir = traj_dir
        (traj_dir / "args.yaml").write_text("asdf")

    def on_instance_start(self, *, index: int, instance: dict[str, Any]):
        instance_id = instance["instance_id"]
        dct = {
            "info": {"exit_status": "submitted"},
        }
        (self._traj_dir / f"{instance_id}.traj").write_text(json.dumps(dct))


@pytest.mark.slow()
def test_existing_corrupted_args(test_script_args: ScriptArguments):
    main = Main(test_script_args)
    main.add_hook(CreateFakeLogFile())
    main.main()


@pytest.mark.slow()
def test_main_hook(test_script_args: ScriptArguments):
    main = Main(test_script_args)
    main.add_hook(MainHook())
    main.main()


@pytest.mark.slow()
def test_agent_with_hook(test_script_args: ScriptArguments):
    main = Main(test_script_args)
    main.agent.add_hook(AgentHook())
    main.main()


PERSISTENT_CONTAINER_NAME = "sweagent-test-persistent-container"


@pytest.fixture()
def _cleanup_persistent_container():
    yield
    client = docker.from_env()
    container = client.containers.get(PERSISTENT_CONTAINER_NAME)
    container.remove(force=True)


@pytest.mark.slow()
@pytest.mark.usefixtures("_cleanup_persistent_container")
def test_agent_persistent_container(test_script_args: ScriptArguments, capsys):
    test_script_args = dataclasses.replace(
        test_script_args,
        environment=dataclasses.replace(test_script_args.environment, container_name=PERSISTENT_CONTAINER_NAME),
    )
    assert test_script_args.environment.verbose
    main = Main(test_script_args)
    assert main.env.logger.isEnabledFor(logging.DEBUG)
    main.main()
    captured = capsys.readouterr()
    print("---")
    print(captured.out)
    print("---")
    print(captured.err)
    print("---")
    text = captured.out + captured.err
    assert "Trying to clone from non-mirror..." in text
    assert "Falling back to full cloning method" in text
