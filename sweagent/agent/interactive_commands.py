from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from simple_parsing.helpers.serialization.serializable import FrozenSerializable


@dataclass(frozen=True)
class InteractiveSessionConfig(FrozenSerializable):
    cmdline: str
    terminal_prompt_pattern: str
    start_command: str
    exit_command: str
    quit_commands_in_session: list = field(default_factory=list)
    signal_for_interrupt_limit: int = 3
    timeout_duration_on_interrupt: int = 5


@dataclass
class InteractiveSession:
    name: str
    session_process: subprocess.Popen


INTERACTIVE_SESSIONS_CONFIG = {
    "gdb": InteractiveSessionConfig(
        cmdline="gdb",
        terminal_prompt_pattern="(gdb) ",
        start_command="debug_start",
        exit_command="debug_stop",
        quit_commands_in_session=["quit"],
    ),
    "connect": InteractiveSessionConfig(
        cmdline="/root/commands/_connect",
        terminal_prompt_pattern="(nc) ",
        start_command="connect_start",
        exit_command="connect_stop",
        quit_commands_in_session=["quit"],
    ),
}
