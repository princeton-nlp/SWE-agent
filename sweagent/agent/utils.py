import re
from collections.abc import Callable


def _guard_multiline_input(action: str, match_fct: Callable[[str], re.Match | None]) -> str:
    """Split action by multiline commands, then append the first line in each multiline command with "<< '{end_name}'".
    Multiline commands (which are specified by an end_name) are commands that span multiple lines and are terminated by a specific end_name.

    Their multi-line argument is sent using a heredoc, which is a way to send a multi-line string to a command in bash.
    """
    parsed_action = []
    rem_action = action
    while rem_action.strip():
        first_match = match_fct(rem_action)
        if first_match:
            pre_action = rem_action[: first_match.start()]
            match_action = rem_action[first_match.start() : first_match.end()]
            rem_action = rem_action[first_match.end() :]
            if pre_action.strip():
                parsed_action.append(pre_action)
            if match_action.strip():
                eof = first_match.group(3).strip()
                if not match_action.split("\n")[0].strip().endswith(f"<< '{eof}'"):
                    guarded_command = match_action[first_match.start() :]
                    first_line = guarded_command.split("\n")[0]
                    guarded_command = guarded_command.replace(first_line, first_line + f" << '{eof}'", 1)
                    parsed_action.append(guarded_command)
                else:
                    parsed_action.append(match_action)
        else:
            parsed_action.append(rem_action)
            rem_action = ""
    return "\n".join(parsed_action)
