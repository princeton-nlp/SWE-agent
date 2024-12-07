from sweagent.agent.problem_statement import ProblemStatement, ProblemStatementConfig
from sweagent.environment.swe_env import SWEEnv
from sweagent.types import AgentRunResult


class RunHook:
    """Hook structure for the web server or other addons to interface with"""

    def on_init(self, *, run):
        """Called when hook is initialized"""

    def on_start(self):
        """Called at the beginning of `Main.main`"""

    def on_end(self):
        """Called at the end of `Main.main`"""

    def on_instance_start(
        self, *, index: int, env: SWEEnv, problem_statement: ProblemStatement | ProblemStatementConfig
    ):
        """Called at the beginning of each instance loop in `Main.run`"""

    def on_instance_skipped(
        self,
    ):
        """Called when an instance is skipped in `Main.run`"""

    def on_instance_completed(self, *, result: AgentRunResult):
        """Called when an instance is completed in `Main.run`"""


class CombinedRunHooks(RunHook):
    def __init__(self):
        self._hooks = []

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

    def on_instance_start(
        self, *, index: int, env: SWEEnv, problem_statement: ProblemStatement | ProblemStatementConfig
    ):
        for hook in self._hooks:
            hook.on_instance_start(index=index, env=env, problem_statement=problem_statement)

    def on_instance_skipped(self):
        for hook in self._hooks:
            hook.on_instance_skipped()

    def on_instance_completed(self, *, result: AgentRunResult):
        for hook in self._hooks:
            hook.on_instance_completed(result=result)
