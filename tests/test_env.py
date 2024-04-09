import dataclasses
from pathlib import Path
import pytest
import yaml
from sweagent.environment.swe_env import EnvironmentArguments, SWEEnv


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
def test_open_pr(test_env_args):
    env = SWEEnv(test_env_args)
    env.reset()
    env.open_pr(_dry_run=True, trajectory=[])


@pytest.mark.slow
def test_interrupt_close(test_env_args):
    env = SWEEnv(test_env_args)
    env.interrupt()
    env.close()