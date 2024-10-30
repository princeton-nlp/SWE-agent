from pathlib import Path
from typing import Any

from run import ScriptArguments
from sweagent.agent.agents import Agent
from sweagent.environment.swe_env import SWEEnv


class MainHook:
    """Hook structure for the web server or other addons to interface with"""

    @staticmethod
    def _is_promising_patch(info: dict[str, Any]) -> bool:
        """Do we actually believe that the patch will solve the issue?
        Or are we just submitting the last patch we generated before hitting an error?
        """
        # The exit status can also be `submitted (exit_cost)` etc.
        return info["exit_status"] == "submitted" and info.get("submission") is not None

    def on_init(self, *, args: ScriptArguments, agent: Agent, env: SWEEnv, traj_dir: Path):
        """Called when hook is initialized"""

    def on_start(self):
        """Called at the beginning of `Main.main`"""

    def on_end(self):
        """Called at the end of `Main.main`"""

    def on_instance_start(self, *, index: int, instance: dict[str, Any]):
        """Called at the beginning of each instance loop in `Main.run`"""

    def on_instance_skipped(
        self,
    ):
        """Called when an instance is skipped in `Main.run`"""

    def on_instance_completed(self, *, info, trajectory):
        """Called when an instance is completed in `Main.run`"""
