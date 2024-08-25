from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from simple_parsing.helpers.serialization.serializable import FrozenSerializable


@dataclass(frozen=True)
class InteractiveSessionConfig(FrozenSerializable):
    terminal_prompt_pattern: str
    start_command: str
    exit_command: str
    quit_commands_in_session: list = field(default_factory=list)


@dataclass
class InteractiveSession:
    name: str
    session_process: subprocess.Popen


INTERACTIVE_SESSIONS_CONFIG = {
    "gdb": InteractiveSessionConfig(
        terminal_prompt_pattern="(gdb) ",
        start_command="debug_start",
        exit_command="debug_stop",
        quit_commands_in_session=["quit"],
    ),
}
