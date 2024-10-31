from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest

from sweagent.environment.config.deployment import DockerDeploymentConfig
from sweagent.environment.config.problem_statement import FileProblemStatement
from sweagent.environment.config.repo import LocalRepoConfig
from sweagent.environment.swe_env import EnvironmentInstanceConfig, SWEEnv

# this is a hack and should be removed when we have a better solution
_this_dir = Path(__file__).resolve().parent
root_dir = _this_dir.parent
package_dir = root_dir / "sweagent"
sys.path.insert(0, str(root_dir))
sys.path.insert(1, str(package_dir))


@pytest.fixture
def test_data_path() -> Path:
    p = _this_dir / "test_data"
    assert p.is_dir()
    return p


@pytest.fixture
def test_trajectories_path(test_data_path) -> Path:
    p = test_data_path / "trajectories"
    assert p.is_dir()
    return p


@pytest.fixture
def test_ctf_trajectories_path(test_data_path) -> Path:
    p = test_data_path / "trajectories" / "ctf"
    assert p.is_dir()
    return p


@pytest.fixture
def ctf_data_path(test_data_sources_path) -> Path:
    p = test_data_sources_path / "ctf"
    assert p.is_dir()
    return p


@pytest.fixture
def test_data_sources_path(test_data_path) -> Path:
    p = test_data_path / "data_sources"
    assert p.is_dir()
    return p


@pytest.fixture
def test_trajectory_path(test_trajectories_path) -> Path:
    traj = (
        test_trajectories_path
        / "gpt4__swe-agent__test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1"
        / "swe-agent__test-repo-i1.traj"
    )
    assert traj.exists()
    return traj


@pytest.fixture
def test_trajectory(test_trajectory_path):
    return json.loads(test_trajectory_path.read_text())


@pytest.fixture(scope="module")
def test_env_args(
    tmpdir_factory,
) -> Generator[EnvironmentInstanceConfig]:
    """This will use a persistent container"""
    local_repo_path = tmpdir_factory.getbasetemp() / "test-repo"
    clone_cmd = ["git", "clone", "https://github.com/swe-agent/test-repo", str(local_repo_path)]
    subprocess.run(clone_cmd, check=True)
    data_path = local_repo_path / "problem_statements" / "1.md"
    test_env_args = EnvironmentInstanceConfig(
        problem_statement=FileProblemStatement(path=str(data_path)),
        deployment=DockerDeploymentConfig(image="sweagent/swe-agent:latest"),
        repo=LocalRepoConfig(path=str(local_repo_path)),
    )
    yield test_env_args
    shutil.rmtree(local_repo_path)


@contextmanager
def swe_env_context(env_args):
    """Context manager to make sure we close the shell on the container
    so that we can reuse it.
    """

    env = SWEEnv.from_config(env_args)
    env.start()
    try:
        yield env
    finally:
        env.close()
