from sweagent.environment.config.repo import RepoConfig


class EnvHook:
    """Hook to be used in `SWEEnv`.

    Subclass this class, add functionality and add it with `SWEEEnv.add_hook(hook)`.
    This allows to inject custom functionality at different stages of the environment
    lifecycle, in particular to connect SWE-agent to a new interface (like a GUI).
    """

    def on_init(self, *, env) -> None:
        """Gets called when the hook is added"""

    def on_copy_repo_started(self, repo: RepoConfig) -> None:
        """Gets called when the repository is being cloned to the container"""

    def on_install_env_started(self) -> None:
        """Called when we start installing the environment"""

    def on_close(self):
        """Called when the environment is closed"""

    def on_environment_startup(self) -> None:
        """Called when the environment is started"""
