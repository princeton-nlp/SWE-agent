from __future__ import annotations

import subprocess

import pytest

from sweagent import CONFIG_DIR
from sweagent.environment.config.deployment import DockerDeploymentConfig
from sweagent.environment.config.repo import LocalRepoConfig
from sweagent.run.run_replay import RunReplay, RunReplayConfig


@pytest.fixture
def rr_config(swe_agent_test_repo_traj, tmp_path, swe_agent_test_repo_clone):
    return RunReplayConfig(
        traj_path=swe_agent_test_repo_traj,
        config_path=CONFIG_DIR / "default_from_url.yaml",
        deployment=DockerDeploymentConfig(),
        output_dir=tmp_path,
        repo=LocalRepoConfig(path=swe_agent_test_repo_clone),
    )


def test_replay(rr_config):
    rr = RunReplay.from_config(rr_config, _catch_errors=False, _require_zero_exit_code=True)
    rr.main()


def test_run_cli_help():
    args = [
        "sweagent",
        "run-replay",
        "--help",
    ]
    subprocess.run(args, check=True)
