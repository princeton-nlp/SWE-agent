import dataclasses
import os
from pathlib import Path
import subprocess
import pytest
import yaml
from sweagent.environment.swe_env import EnvHook, EnvironmentArguments, SWEEnv
from contextlib import contextmanager
import docker


@pytest.fixture(scope="module")
def test_env_args(tmpdir_factory, ):
    """This will use a persistent container"""
    local_repo_path = tmpdir_factory.getbasetemp() / "swe-agent-test-repo"
    clone_cmd = ["git", "clone", "https://github.com/klieret/swe-agent-test-repo", local_repo_path]
    subprocess.run(clone_cmd, check=True)
    data_path = local_repo_path / "problem_statements" / "1.md"
    test_env_args = EnvironmentArguments(
        data_path=str(data_path),
        repo_path=str(local_repo_path),
        image_name="sweagent/swe-agent:latest",
        container_name="test-container-134245890345098",
    )
    yield test_env_args
    # Cleanup (after session ends)
    client = docker.from_env()
    container = client.containers.get(test_env_args.container_name)
    container.remove(force=True)


@contextmanager
def swe_env_context(env_args):
    """Context manager to make sure we close the shell on the container
    so that we can reuse it.
    """

    env = SWEEnv(env_args)
    try:
        yield env
    finally:
        env.close()


@pytest.mark.slow
def test_init_swe_env(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow
def test_init_swe_env_non_persistent(test_env_args):
    test_env_args = dataclasses.replace(test_env_args, container_name=None)
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow
def test_execute_setup_script(tmp_path, test_env_args):
    test_script = "echo 'hello world'"
    script_path = Path(tmp_path / "test_script.sh")
    script_path.write_text(test_script)
    test_env_args = dataclasses.replace(test_env_args, environment_setup=script_path)
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow
def test_execute_environment(tmp_path, test_env_args):
    test_env = {
        "python": "3.6",
        "packages": "pytest",
        "pip_packages": ["tox"],
        "install": "echo 'installing'",
    }
    env_config_path = Path(tmp_path / "env_config.yml")
    env_config_path.write_text(yaml.dump(test_env))
    test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path)
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow
def test_open_pr(test_env_args):
    test_env_args = dataclasses.replace(test_env_args, data_path="https://github.com/klieret/swe-agent-test-repo/issues/1", repo_path="")
    with swe_env_context(test_env_args) as env:
        env.reset()
        env.open_pr(_dry_run=True, trajectory=[])


@pytest.mark.slow
def test_interrupt_close(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.reset()
        env.interrupt()


@pytest.mark.slow
def test_communicate_old(test_env_args):
    del os.environ["SWE_AGENT_EXPERIMENTAL_COMMUNICATE"]
    try:
        with swe_env_context(test_env_args) as env:
            env.reset()
    except:
        raise
    finally:
        os.environ["SWE_AGENT_EXPERIMENTAL_COMMUNICATE"] = "1"


@pytest.mark.slow
def test_env_with_hook(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.add_hook(EnvHook())
        env.reset()