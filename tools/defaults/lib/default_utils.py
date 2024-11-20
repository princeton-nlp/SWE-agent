import json
import os
from pathlib import Path, PurePath

SWE_AGENT_ENV_FILE = Path(os.environ.get("SWE_AGENT_ENV_FILE", "/root/.swe-agent-env"))


def read_env(var_name, default_value=None):
    if not SWE_AGENT_ENV_FILE.exists():
        SWE_AGENT_ENV_FILE.write_text("{}")
        return default_value
    env = json.loads(SWE_AGENT_ENV_FILE.read_text())
    return env.get(var_name, default_value)


def write_env(var_name, var_value):
    if not SWE_AGENT_ENV_FILE.exists():
        SWE_AGENT_ENV_FILE.write_text("{}")
    env = json.loads(SWE_AGENT_ENV_FILE.read_text())
    env[var_name] = var_value
    SWE_AGENT_ENV_FILE.write_text(json.dumps(env))


def get_current_file():
    return Path(read_env("CURRENT_FILE"))  # type: ignore


def get_current_line():
    return int(read_env("CURRENT_LINE"))  # type: ignore


def get_current_file_with_line_range(file_path: str | PurePath | None = None) -> tuple[Path, int, int]:
    """Returns 0-based index of the first and last line to print."""
    if file_path is None:
        _spec = read_env("CURRENT_FILE")
        assert _spec, "CURRENT_FILE is not set"
        file_path = Path(_spec)
    else:
        file_path = Path(file_path)
    current_line = int(read_env("CURRENT_LINE"))  # type: ignore
    window = int(read_env("WINDOW"))  # type: ignore
    n_lines = file_path.read_text().count("\n") + 1
    return (
        file_path,
        max(0, current_line - 1 - window // 2),
        min(current_line - 1 + window // 2, n_lines - 1),
    )


def print_window(file_path: str | PurePath | None = None, start_line: int | None = None, end_line: int | None = None):
    """

    Args:
        start_line: 0-indexed line number
        end_line: 0-indexed line number (inclusive)
    """
    file_path, start_line, end_line = get_current_file_with_line_range(file_path)
    lines = Path(file_path).read_text().splitlines()
    print(f"[File: {file_path} ({len(lines)} lines total)]")
    if start_line > 0:
        print(f"({start_line} more lines above)")
    for i, line in enumerate(lines[start_line : end_line + 1]):
        print(f"{i+1}:{line}")
    if end_line < len(lines) - 1:
        print(f"({len(lines) - end_line - 1} more lines below)")
