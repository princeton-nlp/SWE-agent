from __future__ import annotations

import io
import sys

from flask_socketio import SocketIO

from sweagent import PACKAGE_DIR
from sweagent.agent.hooks.abstract import AbstractAgentHook
from sweagent.api.utils import strip_ansi_sequences
from sweagent.environment.hooks.abstract import EnvHook

# baaaaaaad
sys.path.append(str(PACKAGE_DIR.parent))
from sweagent.run.hooks.abstract import RunHook


class StreamToSocketIO(io.StringIO):
    def __init__(
        self,
        wu: WebUpdate,
    ):
        super().__init__()
        self._wu = wu

    def write(self, message):
        message = strip_ansi_sequences(message)
        self._wu.up_log(message)

    def flush(self):
        pass


class WebUpdate:
    """This class talks to socketio. It's pretty much a wrapper around socketio.emit."""

    def __init__(self, socketio: SocketIO):
        self._socketio = socketio
        self.log_stream = StreamToSocketIO(self)

    def _emit(self, event, data):
        """Directly wrap around socketio.emit"""
        self._socketio.emit(event, data)

    def up_log(self, message: str):
        """Update the log"""
        self._emit("log_message", {"message": message})

    def up_banner(self, message: str):
        """Update the banner"""
        self._emit("update_banner", {"message": message})

    def up_agent(
        self,
        message: str,
        *,
        format: str = "markdown",
        thought_idx: int | None = None,
        type_: str = "info",
    ):
        """Update the agent feed"""
        self._emit(
            "update",
            {
                "feed": "agent",
                "message": message,
                "format": format,
                "thought_idx": thought_idx,
                "type": type_,
            },
        )

    def up_env(
        self,
        message: str,
        *,
        type_: str,
        format: str = "markdown",
        thought_idx: int | None = None,
    ):
        """Update the environment feed"""
        self._emit(
            "update",
            {
                "feed": "env",
                "message": message,
                "format": format,
                "thought_idx": thought_idx,
                "type": type_,
            },
        )

    def finish_run(self):
        """Finish the run. We use that to control which buttons are active."""
        self._emit("finish_run", {})


class MainUpdateHook(RunHook):
    def __init__(self, wu: WebUpdate):
        """This hooks into the Main class to update the web interface"""
        self._wu = wu

    def on_start(self):
        self._wu.up_env(message="Environment container initialized", format="text", type_="info")

    def on_end(self):
        self._wu.up_agent(message="The run has ended", format="text")
        self._wu.finish_run()

    def on_instance_completed(self, *, info, trajectory):
        print(info.get("submission"))
        if info.get("submission") and info["exit_status"] == "submitted":
            msg = (
                "The submission was successful. You can find the patch (diff) in the right panel. "
                "To apply it to your code, run `git apply /path/to/patch/file.patch`. "
            )
            self._wu.up_agent(msg, type_="success")


class AgentUpdateHook(AbstractAgentHook):
    def __init__(self, wu: WebUpdate):
        """This hooks into the Agent class to update the web interface"""
        self._wu = wu
        self._sub_action = None
        self._thought_idx = 0

    def on_actions_generated(self, *, thought: str, action: str, output: str):
        self._thought_idx += 1
        for prefix in ["DISCUSSION\n", "THOUGHT\n", "DISCUSSION", "THOUGHT"]:
            thought = thought.replace(prefix, "")
        self._wu.up_agent(
            message=thought,
            format="markdown",
            thought_idx=self._thought_idx,
            type_="thought",
        )

    def on_sub_action_started(self, *, sub_action: dict):
        # msg = f"```bash\n{sub_action['action']}\n```"
        msg = "$ " + sub_action["action"].strip()
        self._sub_action = sub_action["action"].strip()
        self._wu.up_env(message=msg, thought_idx=self._thought_idx, type_="command")

    def on_sub_action_executed(self, *, obs: str, done: bool):
        type_ = "output"
        if self._sub_action == "submit":
            type_ = "diff"
        if obs is None:
            # This can happen for empty patch submissions
            obs = ""
        msg = obs.strip()
        self._wu.up_env(message=msg, thought_idx=self._thought_idx, type_=type_)


class EnvUpdateHook(EnvHook):
    def __init__(self, wu: WebUpdate):
        """This hooks into the environment class to update the web interface"""
        self._wu = wu

    def on_close(self):
        self._wu.up_env(message="Environment closed", format="text", type_="info")

    # def on_query_message_added(
    #         self,
    #         *,
    #         role: str,
    #         content: str,
    #         agent: str,
    #         is_demo: bool = False,
    #         thought: str = "",
    #         action: str = ""
    #     ):
    #     if role == "assistant":
    #         return
    #     if thought or action:
    #         return
    #     if is_demo:
    #         return self._wu.up_agent(title="Demo", message=content, thought_idx=self._thought_idx + 1)
    #     self._wu.up_agent(title="Query", message=content, thought_idx=self._thought_idx + 1)
