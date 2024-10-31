from __future__ import annotations

import subprocess
from typing import Any

import pytest

from sweagent.agent.agents import AgentConfig
from sweagent.environment.swe_env import EnvironmentInstanceConfig
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
    def on_instance_start(self, *, index: int, instance: dict[str, Any]):
        msg = "test exception"
        raise ValueError(msg)


@pytest.mark.slow
def test_run_single_raises_exception():
    rs = RunSingle.from_config(RunSingleConfig())
    rs.add_hook(RaisesExceptionHook())
    with pytest.raises(ValueError, match="test exception"):
        rs.main()


@pytest.fixture
def agent_config_with_commands():
    ac = AgentConfig()
    ac.command_files = [
        f"config/commands/{name}"
        for name in ["defaults.sh", "search.sh", "edit_linting.sh", "_split_string.py", "submit.sh"]
    ]
    return ac


@pytest.mark.slow
def test_run_instant_empty_submit(agent_config_with_commands):
    ac = agent_config_with_commands
    ac.model.name = "instant_empty_submit"
    rsc = RunSingleConfig(
        env=EnvironmentInstanceConfig(),
        agent=ac,
    )
    rs = RunSingle.from_config(rsc)
    rs.main()
