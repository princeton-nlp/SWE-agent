from __future__ import annotations

import dataclasses
import time
from pathlib import Path
from unittest import mock

import pytest
import yaml

import docker
import docker.errors
from sweagent import CONFIG_DIR
from sweagent.environment.swe_env import EnvHook, EnvironmentArguments

from .conftest import swe_env_context


@pytest.mark.slow
def test_init_swe_env(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow
def test_init_swe_env_conservative_clone(test_env_args):
    with mock.patch.dict("os.environ", {"SWE_AGENT_CLONE_METHOD": "full"}):
        with swe_env_context(test_env_args) as env:
            env.reset()


@pytest.mark.slow
def test_init_swe_env_non_persistent(test_env_args):
    test_env_args = dataclasses.replace(test_env_args, container_name=None)
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow
def test_init_swe_env_cached_task_image(test_env_args):
    test_env_args = dataclasses.replace(test_env_args, cache_task_images=True, container_name=None)
    start = time.perf_counter()
    with swe_env_context(test_env_args) as env:
        env.reset()
    duration_no_cache = time.perf_counter() - start
    start = time.perf_counter()
    # now it should be cached, so let's run again
    image_prefix = None
    with swe_env_context(test_env_args) as env:
        env.reset()
        image_prefix = env.cached_image_prefix
    assert image_prefix
    duration_cache = time.perf_counter() - start
    assert duration_cache < duration_no_cache
    # Retrieve all images with a prefix "prefix"
    client = docker.from_env()
    # Remove the images
    for image in client.images.list():
        if not image.tags:
            continue
        if not image.tags[0].startswith(image_prefix):
            continue
        client.images.remove(image.id)


@pytest.mark.slow
def test_execute_setup_script(tmp_path, test_env_args):
    test_script = "echo 'hello world'"
    script_path = Path(tmp_path / "test_script.sh")
    script_path.write_text(test_script)
    test_env_args = dataclasses.replace(test_env_args, environment_setup=script_path)
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow
def test_read_file(tmp_path, test_env_args):
    with swe_env_context(test_env_args) as env:
        env.reset()
        content = env.read_file(Path("tests/filetoread.txt"))
        assert content.splitlines()[-1].strip() == "SWEEnv.read_file"


@pytest.mark.slow
def test_execute_environment(tmp_path, test_env_args, capsys):
    test_env = {
        "python": "3.11",
        "packages": "pytest",
        "pip_packages": ["tox"],
        "install": "python -m pip install --upgrade pip && python -m pip install -e .",
    }
    env_config_path = Path(tmp_path / "env_config.yml")
    env_config_path.write_text(yaml.dump(test_env))
    # Make sure we don't use persistent container, else we might have already installed the conda environment
    test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path, container_name=None)
    with swe_env_context(test_env_args) as env:
        env.reset()
    out = capsys.readouterr().out
    print(out)
    assert "Cloned python conda environment" not in out


@pytest.mark.slow
def test_execute_environment_default(test_env_args):
    env_config_paths = (CONFIG_DIR / "environment_setup").iterdir()
    assert env_config_paths
    # Make sure we don't use persistent container, else we might have already installed the conda environment
    test_env_args = dataclasses.replace(test_env_args, container_name=None)
    for env_config_path in env_config_paths:
        if env_config_path.name == "django.yaml":
            continue
        if env_config_path.suffix not in [".yaml", ".yml", ".sh"]:
            continue
        print(env_config_path)
        test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path)
        with swe_env_context(test_env_args) as env:
            env.reset()


@pytest.mark.slow
def test_execute_environment_clone_python(tmp_path, test_env_args, capsys):
    """This should clone the existing python 3.10 conda environment for speedup"""
    test_env = {
        "python": "3.10",
        "packages": "pytest",
        "pip_packages": ["tox"],
        "install": "python -m pip install --upgrade pip && python -m pip install -e .",
    }
    env_config_path = Path(tmp_path / "env_config.yml")
    env_config_path.write_text(yaml.dump(test_env))
    # Make sure we don't use persistent container, else we might have already installed the conda environment
    test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path, container_name=None)
    with swe_env_context(test_env_args) as env:
        env.reset()
    out = capsys.readouterr().out
    print(out)
    assert "Cloned python conda environment" in out


@pytest.mark.slow
def test_open_pr(test_env_args):
    test_env_args = dataclasses.replace(
        test_env_args,
        data_path="https://github.com/swe-agent/test-repo/issues/1",
        repo_path="",
    )
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
    with mock.patch.dict("os.environ", {"SWE_AGENT_COMMUNICATE_METHOD": "processes"}):
        with swe_env_context(test_env_args) as env:
            env.reset()


@pytest.mark.slow
def test_env_with_hook(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.add_hook(EnvHook())
        env.reset()


def test_invalid_config():
    with pytest.raises(ValueError, match=".*Not allowed.*"):
        EnvironmentArguments(
            data_path=".",
            container_name="test",
            cache_task_images=True,
        )
