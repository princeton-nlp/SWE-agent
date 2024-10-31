from typing import Any

from sweagent.environment.swe_env import SWEEnv


class RunHook:
    """Hook structure for the web server or other addons to interface with"""

    @staticmethod
    def _is_promising_patch(info: dict[str, Any]) -> bool:
        """Do we actually believe that the patch will solve the issue?
        Or are we just submitting the last patch we generated before hitting an error?
        """
        # The exit status can also be `submitted (exit_cost)` etc.
        return info["exit_status"] == "submitted" and info.get("submission") is not None

    def on_init(self, *, run):
        """Called when hook is initialized"""

    def on_start(self):
        """Called at the beginning of `Main.main`"""

    def on_end(self):
        """Called at the end of `Main.main`"""

    def on_instance_start(self, *, index: int, env: SWEEnv):
        """Called at the beginning of each instance loop in `Main.run`"""

    def on_instance_skipped(
        self,
    ):
        """Called when an instance is skipped in `Main.run`"""

    def on_instance_completed(self, *, info, trajectory):
        """Called when an instance is completed in `Main.run`"""


class CombinedRunHooks(RunHook):
    def __init__(self, hooks: list[RunHook] | None = None):
        self._hooks = hooks or []

    def add_hook(self, hook: RunHook) -> None:
        self._hooks.append(hook)

    @property
    def hooks(self) -> list[RunHook]:
        return self._hooks

    def on_init(self, *, run):
        for hook in self._hooks:
            hook.on_init(run=run)

    def on_start(self):
        for hook in self._hooks:
            hook.on_start()

    def on_end(self):
        for hook in self._hooks:
            hook.on_end()

    def on_instance_start(self, *, index: int, env: SWEEnv):
        for hook in self._hooks:
            hook.on_instance_start(index=index, env=env)

    def on_instance_skipped(self):
        for hook in self._hooks:
            hook.on_instance_skipped()

    def on_instance_completed(self, *, info, trajectory):
        for hook in self._hooks:
            hook.on_instance_completed(info=info, trajectory=trajectory)
