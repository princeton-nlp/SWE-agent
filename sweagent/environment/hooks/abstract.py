from sweagent.environment.repo import Repo, RepoConfig


class EnvHook:
    """Hook to be used in `SWEEnv`.

    Subclass this class, add functionality and add it with `SWEEEnv.add_hook(hook)`.
    This allows to inject custom functionality at different stages of the environment
    lifecycle, in particular to connect SWE-agent to a new interface (like a GUI).
    """

    def on_init(self, *, env) -> None:
        """Gets called when the hook is added"""

    def on_copy_repo_started(self, repo: RepoConfig | Repo) -> None:
        """Gets called when the repository is being cloned to the container"""

    def on_start_deployment(self) -> None:
        """Gets called when the deployment is being started"""

    def on_install_env_started(self) -> None:
        """Called when we start installing the environment"""

    def on_close(self):
        """Called when the environment is closed"""

    def on_environment_startup(self) -> None:
        """Called when the environment is started"""


class CombinedEnvHooks(EnvHook):
    def __init__(self):
        self._hooks = []

    def add_hook(self, hook: EnvHook) -> None:
        self._hooks.append(hook)

    def on_init(self, *, env) -> None:
        for hook in self._hooks:
            hook.on_init(env=env)

    def on_copy_repo_started(self, repo: RepoConfig | Repo) -> None:
        for hook in self._hooks:
            hook.on_copy_repo_started(repo=repo)

    def on_start_deployment(self) -> None:
        for hook in self._hooks:
            hook.on_start_deployment()

    def on_install_env_started(self) -> None:
        for hook in self._hooks:
            hook.on_install_env_started()

    def on_close(self):
        for hook in self._hooks:
            hook.on_close()

    def on_environment_startup(self) -> None:
        for hook in self._hooks:
            hook.on_environment_startup()
