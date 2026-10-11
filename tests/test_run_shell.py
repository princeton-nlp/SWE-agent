from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import sweagent.run.run_shell as run_shell_module
from sweagent.run.run_shell import run_from_cli


def _patch_run_shell_dependencies(monkeypatch, repo_answer: str | None):
    """Replace everything in run_shell that touches the terminal, the network or docker.

    Returns the list of environment configs passed to ``SWEEnv.from_config``.
    """

    def fake_ask(prompt, **kwargs):
        if repo_answer is not None and "Repository path" in str(prompt):
            return repo_answer
        msg = f"Unexpected prompt: {prompt}"
        raise AssertionError(msg)

    captured_env_configs = []

    class FakeSWEEnv:
        @classmethod
        def from_config(cls, config):
            captured_env_configs.append(config)
            return MagicMock()

    class FakeRunShell:
        def __init__(self, env, agent, problem_statement, *, output_dir=Path("."), hooks=None):
            self.env = env
            self.agent = agent
            self.problem_statement = problem_statement

        def run(self):
            pass

    monkeypatch.setattr(run_shell_module, "Prompt", SimpleNamespace(ask=fake_ask))
    monkeypatch.setattr(run_shell_module, "SWEEnv", FakeSWEEnv)
    monkeypatch.setattr(run_shell_module, "ShellAgent", SimpleNamespace(from_config=lambda config: MagicMock()))
    monkeypatch.setattr(run_shell_module, "RunShell", FakeRunShell)
    return captured_env_configs


def test_run_shell_repo_prompt_reaches_docker_args(monkeypatch, tmp_path):
    """The repo path entered at the interactive prompt must end up in the docker volume
    mount instead of the string representation of ``None``.
    """
    repo_path = tmp_path / "myrepo"
    captured_env_configs = _patch_run_shell_dependencies(monkeypatch, repo_answer=str(repo_path))
    run_from_cli(["-p", "fix the bug"])
    assert len(captured_env_configs) == 1
    docker_args = captured_env_configs[0].deployment.docker_args
    assert docker_args == ["-v", f"{repo_path}:/repo"]


def test_run_shell_cli_repo_reaches_docker_args(monkeypatch, tmp_path):
    """The repo path given with ``-r`` must end up in the docker volume mount."""
    repo_path = tmp_path / "myrepo"
    captured_env_configs = _patch_run_shell_dependencies(monkeypatch, repo_answer=None)
    run_from_cli(["-p", "fix the bug", "-r", str(repo_path)])
    assert len(captured_env_configs) == 1
    docker_args = captured_env_configs[0].deployment.docker_args
    assert docker_args == ["-v", f"{repo_path}:/repo"]
