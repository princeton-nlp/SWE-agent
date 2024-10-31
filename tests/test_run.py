from __future__ import annotations

import subprocess

import pytest

from sweagent.agent.agents import AgentConfig
from sweagent.environment.swe_env import EnvironmentInstanceConfig
from sweagent.run._common import BasicCLI
from sweagent.run.hooks.abstract import RunHook
from sweagent.run.run_single import RunSingle, RunSingleConfig


@pytest.mark.slow
def test_run_cli_help():
    args = [
        "python",
        "sweagent/run/run_single.py",
        "--help",
    ]
    subprocess.run(args, check=True)


class RaisesExceptionHook(RunHook):
    def on_instance_start(self, *args, **kwargs):
        msg = "test exception"
        raise ValueError(msg)


@pytest.mark.slow
def test_run_single_raises_exception():
    rs = RunSingle.from_config(RunSingleConfig())
    rs.add_hook(RaisesExceptionHook())
    with pytest.raises(ValueError, match="test exception"):
        rs.run()


@pytest.fixture
def agent_config_with_commands():
    ac = AgentConfig()
    ac.command_files = [
        f"config/commands/{name}"
        for name in ["defaults.sh", "search.sh", "edit_linting.sh", "_split_string.py", "submit.sh"]
    ]
    return ac


@pytest.mark.slow
def test_run_ies(agent_config_with_commands):
    # ies = instant empty submit
    ac = agent_config_with_commands
    ac.model.name = "instant_empty_submit"
    rsc = RunSingleConfig(
        env=EnvironmentInstanceConfig(),
        agent=ac,
    )
    rs = RunSingle.from_config(rsc)
    rs.run()


@pytest.mark.slow
@pytest.mark.parametrize("repo", ["local", "github"])
@pytest.mark.parametrize("problem_statement_source", ["github", "local", "text"])
def test_run_ies_repo_ps_matrix(
    tmpdir,
    swe_agent_test_repo_clone,
    repo,
    problem_statement_source,
):
    if problem_statement_source == "github":
        ps_args = ["--env.problem_statement.url", "https://github.com/swe-agent/test-repo/issues/1"]
    elif problem_statement_source == "local":
        ps_args = ["--env.problem_statement.path", str(swe_agent_test_repo_clone / "problem_statements" / "1.md")]
    elif problem_statement_source == "text":
        ps_args = ["--env.problem_statement.text='this is a test'"]
    else:
        raise ValueError(problem_statement_source)
    if repo == "local":
        repo_args = ["--env.repo.path", str(swe_agent_test_repo_clone)]
    elif repo == "github":
        repo_args = ["--env.repo.url", "https://github.com/swe-agent/test-repo"]
    else:
        raise ValueError(repo)
    args = [
        "--agent.model.name=instant_empty_submit",
        "--raise_exceptions=True",
        *ps_args,
        *repo_args,
    ]
    print(args)
    rs_config = BasicCLI(RunSingleConfig).get_args(args)
    print(rs_config)
    rs = RunSingle.from_config(rs_config)  # type: ignore
    with tmpdir.as_cwd():
        # Test that we can run run.py also independently from repo dir
        rs.run()
