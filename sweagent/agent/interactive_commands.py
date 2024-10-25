from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

from sweagent.environment.utils import (
    DOCKER_START_UP_DELAY,
    NoOutputTimeoutError,
    read_session_with_timeout,
    read_with_timeout,
)


@dataclass
class InteractiveSessionConfig:
    cmdline: str
    terminal_prompt_pattern: str
    start_command: str
    exit_command: str
    quit_commands_in_session: list = field(default_factory=list)
    signal_for_interrupt_limit: int = 3
    timeout_duration_on_interrupt: int = 5


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
    "dummy": InteractiveSessionConfig(
        cmdline="/root/commands/_interactive_dummy",
        terminal_prompt_pattern="(dummy) ",
        start_command="dummy_start",
        exit_command="dummy_stop",
        quit_commands_in_session=["stop"],
    ),
}


def get_interactive_commands(output: str, *, logger: logging.Logger) -> tuple[str | None, list[str]]:
    """Function for extracting interactive session commands from dummy output
    of interactive command wrappers that were run in the environment.

    Args:
        output: observation

    Returns:
        session: session name for the commands or None if no commands found.
        commands: list of commands extracted from observation.
    """
    pattern = r"\<\<INTERACTIVE\|\|(.*)\|\|INTERACTIVE\>\>"
    session_pattern = r"SESSION=(.*)"
    session_name = ""
    commands = []
    n_lines_ignored = 0
    for line in output.split("\n"):
        match = re.search(pattern, line, re.DOTALL)
        if match is None:
            if line.strip():
                n_lines_ignored += 1
            continue
        command = match.group(1)
        match = re.search(session_pattern, command, re.DOTALL)
        if match is None:
            commands.append(command)
        else:
            session_name = match.group(1)
    if not session_name:
        if commands:
            logger.error(f"No session name found even though interactive " f"commands {commands!r} were found.")
        return None, []

    if n_lines_ignored:
        logger.error(f"Ignored {n_lines_ignored} lines when parsing interactive commands.")

    return session_name, commands


@dataclass
class InteractiveSession:
    name: str
    session_process: subprocess.Popen
    config: InteractiveSessionConfig
    logger: logging.Logger
    container_name: str
    container_obj: Any

    def _get_only_one_interactive_error_message_observation(self) -> str:
        """Return a warning message about having to quit the existing interactive session before
        starting a new one.
        """
        exit_command = self.config.exit_command
        return f"Interactive session already open. Please close the current interactive session: {self.name} with the command: `{exit_command}`"

    def communicate(
        self,
        input: str,
        *,
        timeout_duration: int | float = 25,
        no_output_timeout_duration: int | float = 25,
    ) -> str:
        """
        Sends input to interactive_session and returns output

        Args:
            input: input to send to session
            timeout_duration: duration to wait for output

        Returns:
            output: output from session
        """
        self.logger.log(logging.TRACE, "Input:\n%s", input)  # type: ignore

        try:
            cmd = input if input.endswith("\n") else input + "\n"
            os.write(self.session_process.stdin.fileno(), cmd.encode())  # type: ignore
            time.sleep(0.03)
            self.session_process.stdin.flush()  # type: ignore
        except BrokenPipeError:
            traceback.print_exc()
            self.logger.error("Failed to communicate with session. Check docker logs for more information.")
            msg = "Failed to communicate with session"
            raise RuntimeError(msg)

        self.logger.debug(f"Command: {input}")
        # if command is to quit the current interactive session, sleep for termination then exit with no observation
        if input.strip() in self.config.quit_commands_in_session:
            time.sleep(1)
            return ""

        try:
            buffer = read_session_with_timeout(
                self.session_process, self.config.terminal_prompt_pattern, timeout_duration, no_output_timeout_duration
            )
        except Exception:
            msg = f"Read with timeout failed on input:\n---\n{input}\n---"
            self.logger.error(msg)
            raise
        self.logger.log(logging.TRACE, "Output:\n%s", buffer)  # type: ignore
        return buffer

    def communicate_with_handling(
        self,
        command: str,
        *,
        timeout_duration: int | float = 25,
        no_output_timeout_duration: int | float = 25,
    ) -> tuple[str, bool]:
        """
        Sends input to interactive_session and returns output.
        This wrapper around communicate handles various exceptions and timeouts.

        Args:
            input: input to send to session
            timeout_duration: duration to wait for output

        Returns:
            output: output from session
        """
        try:
            observation = self.communicate(
                command,
                timeout_duration=timeout_duration,
                no_output_timeout_duration=no_output_timeout_duration,
            )
        except TimeoutError as e:
            try:
                observation = self.interrupt()
                observation += "\nEXECUTION TIMED OUT"
                observation += (
                    f" BECAUSE NO OUTPUT WAS PRODUCED FOR MORE THAN {no_output_timeout_duration} SECONDS.\nPLEASE REFINE YOUR RUNNING COMMAND SO IT WILL PRODUCE OUTPUT IN THE SPECIFIED TIME FRAME."
                    if isinstance(e, NoOutputTimeoutError)
                    else f" BECAUSE THE COMMAND WAS RUNNING FOR MORE THAN {timeout_duration} SECONDS."
                )
            except Exception as e:
                observation = "\nEXECUTION TIMED OUT AND INTERRUPT FAILED. TERMINATING INTERACTIVE SESSION."
                self.logger.warning(f"Failed to interrupt container: {e}\nTERMINATING INTERACTIVE SESSION.")
                return observation, True
        except RuntimeError as e:
            observation = e.args[1] if len(e.args) > 1 else ""
            observation += "\nCOMMAND FAILED TO EXECUTE. TERMINATING INTERACTIVE SESSION."
            self.logger.warning(f"Failed to execute command: {e}\nTERMINATING INTERACTIVE SESSION.")
            return observation, True
        except BrokenPipeError as e:
            observation = "\nBROKEN PIPE ERROR. TERMINATING INTERACTIVE SESSION."
            self.logger.error(f"Broken pipe error: {e}\nTERMINATING INTERACTIVE SESSION.")
            return observation, True
        except Exception:
            observation = "\nEXECUTION FAILED OR COMMAND MALFORMED"
            self.logger.exception("Unknown exception")
            return observation, True
        return observation, False

    def interrupt(
        self,
    ) -> str:
        """
        Send interrupt signal to interactive session several times to see if we can communicate with the process again.
        """
        assert self.container_obj is not None
        for _ in range(self.config.signal_for_interrupt_limit):
            self.container_obj.exec_run(f"pkill -SIGINT {self.name}")
        return read_session_with_timeout(
            self.session_process,
            terminal_pattern=self.config.terminal_prompt_pattern,
            timeout_duration=self.config.timeout_duration_on_interrupt,
            no_output_timeout_duration=self.config.timeout_duration_on_interrupt,
        )


def get_interactive_session(
    ctr_name: str, ctr_obj, cwd: str, session_name: str, config: InteractiveSessionConfig, logger: logging.Logger
) -> tuple[str, InteractiveSession]:
    """
    Starts a new interactive session on the given container name.
    Returns a subprocess.Popen object that is available for further read/writes for submitting commands and reading output.

    Returns:
        observation: observation from starting the interactive session
        session: InteractiveSession object
    """
    startup_cmd = [
        "docker",
        "exec",
        "-i",
        "-w",
        cwd,
        ctr_name,
        config.cmdline,
    ]
    logger.debug(f"Starting interactive session {session_name} with command: {shlex.join(startup_cmd)}")
    session = subprocess.Popen(
        startup_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    time.sleep(DOCKER_START_UP_DELAY)
    observation = read_with_timeout(session, lambda: list(), timeout_duration=1)
    return observation, InteractiveSession(
        name=session_name,
        session_process=session,
        config=config,
        logger=logger,
        container_obj=ctr_obj,
        container_name=ctr_name,
    )
