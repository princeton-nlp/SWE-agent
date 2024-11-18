from collections.abc import Callable

from sweagent.agent.hooks.abstract import AbstractAgentHook


class SetStatusAgentHook(AbstractAgentHook):
    def __init__(self, id: str, callable: Callable[[str, str], None]):
        self._callable = callable
        self._id = id
        self._i_step = 0

    def _update(self, message: str):
        self._callable(self._id, message)

    def on_step_start(self):
        self._i_step += 1
        self._update(f"Step {self._i_step}")
