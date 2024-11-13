from typing import TYPE_CHECKING

from sweagent.agent.models import APIStats
from sweagent.types import AgentInfo, Trajectory, TrajectoryStep

if TYPE_CHECKING:
    # avoid circular import
    from sweagent.agent.agents import Agent


class AbstractAgentHook:
    def on_init(self, *, agent: "Agent"):
        """Note: Depending on the internals of `Agent` should be done with care,
        it's best to use this as little as possible.
        """

    def on_run_start(
        self,
    ): ...

    def on_step_start(self): ...

    def on_actions_generated(self, *, thought: str, action: str, output: str): ...

    def on_action_started(self, *, action: str): ...

    def on_action_executed(self, *, obs: str): ...

    def on_step_done(self, *, trajectory_step: TrajectoryStep, model_stats: APIStats): ...

    def on_run_done(self, *, trajectory: Trajectory, info: AgentInfo): ...

    def on_model_query(self, *, messages: list[dict[str, str]], agent: str):
        """Actually query the model with the complete history."""

    def on_query_message_added(
        self,
        *,
        role: str,
        content: str,
        agent: str,
        is_demo: bool = False,
        thought: str = "",
        action: str = "",
    ): ...

    def on_setup_done(self): ...


class CombinedAgentHook(AbstractAgentHook):
    def __init__(self, hooks: list[AbstractAgentHook] | None = None):
        self._hooks = hooks or []

    def add_hook(self, hook: AbstractAgentHook):
        self._hooks.append(hook)

    @property
    def hooks(self) -> list[AbstractAgentHook]:
        return self._hooks

    def on_init(self, *, agent: "Agent"):
        for hook in self.hooks:
            hook.on_init(agent=agent)

    def on_run_start(self):
        for hook in self.hooks:
            hook.on_run_start()

    def on_step_start(self):
        for hook in self.hooks:
            hook.on_step_start()

    def on_actions_generated(self, *, thought: str, action: str, output: str):
        for hook in self.hooks:
            hook.on_actions_generated(thought=thought, action=action, output=output)

    def on_action_started(self, *, action: str):
        for hook in self.hooks:
            hook.on_action_started(action=action)

    def on_action_executed(self, *, obs: str):
        for hook in self.hooks:
            hook.on_action_executed(obs=obs)

    def on_step_done(self, *, trajectory_step: TrajectoryStep, model_stats: APIStats):
        for hook in self.hooks:
            hook.on_step_done(trajectory_step=trajectory_step, model_stats=model_stats)

    def on_run_done(self, *, trajectory: Trajectory, info: AgentInfo):
        for hook in self.hooks:
            hook.on_run_done(trajectory=trajectory, info=info)

    def on_model_query(self, *, messages: list[dict[str, str]], agent: str):
        for hook in self.hooks:
            hook.on_model_query(messages=messages, agent=agent)

    def on_query_message_added(
        self, *, role: str, content: str, agent: str, is_demo: bool = False, thought: str = "", action: str = ""
    ):
        for hook in self.hooks:
            hook.on_query_message_added(
                role=role, content=content, agent=agent, is_demo=is_demo, thought=thought, action=action
            )
