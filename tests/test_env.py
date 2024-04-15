import dataclasses
import os
from pathlib import Path
import pytest
import yaml
from sweagent.environment.swe_env import EnvironmentArguments, SWEEnv


# TEST_INSTANCE = {"repo": "test/test",
#         "instance_id": "test__test-4764",
#         "base_commit": "",
#         "patch": "",
#         "problem_statement": "",
#         "hints_text": "",
#         "created_at": "2023-04-16T14:24:42Z",
#         "version": "1.4",
#         "FAIL_TO_PASS": [
#         ],
#         "PASS_TO_PASS": [
#         ],
#         "environment_setup_commit": "test"
#     }


@pytest.fixture
def test_env_args():
    test_env_args = EnvironmentArguments(
        data_path="https://github.com/klieret/swe-agent-test-repo/issues/1",
        image_name="sweagent/swe-agent:latest",
    )
    return test_env_args


@pytest.mark.slow
def test_init_swe_env(test_env_args):
    env = SWEEnv(test_env_args)
    env.reset()


@pytest.mark.slow
def test_init_swe_env_persistent(test_env_args):
    test_env_args = dataclasses.replace(test_env_args, container_name="test-container")
    env = SWEEnv(test_env_args)
    env.reset()


@pytest.mark.slow
def test_execute_setup_script(tmp_path, test_env_args):
    test_script = "echo 'hello world'"
    script_path = Path(tmp_path / "test_script.sh")
    script_path.write_text(test_script)
    test_env_args = dataclasses.replace(test_env_args, environment_setup=script_path)
    env = SWEEnv(test_env_args)
    env.reset()


@pytest.mark.slow
def test_execute_environment(tmp_path, test_env_args):
    test_env = {
        "python": "3.6",
        "packages": "pytest",
        "pip_packages": "tox",
        "install": "echo 'installing'",
    }
    env_config_path = Path(tmp_path / "env_config.yml")
    env_config_path.write_text(yaml.dump(test_env))
    test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path)
    env = SWEEnv(test_env_args)
    env.reset()


@pytest.mark.slow
def test_open_pr(test_env_args):
    env = SWEEnv(test_env_args)
    env.reset()
    env.open_pr(_dry_run=True, trajectory=[])


@pytest.mark.slow
def test_interrupt_close(test_env_args):
    env = SWEEnv(test_env_args)
    env.interrupt()
    env.close()


@pytest.mark.slow
def test_communicate_old(test_env_args):
    del os.environ["SWE_AGENT_EXPERIMENTAL_COMMUNICATE"]
    try:
        env = SWEEnv(test_env_args)
        env.reset()
    except:
        raise
    finally:
        os.environ["SWE_AGENT_EXPERIMENTAL_COMMUNICATE"] = "1"