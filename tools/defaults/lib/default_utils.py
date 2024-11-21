import json
import os
from pathlib import Path, PurePath
from typing import Any


class EnvRegistry:
    def __init__(self, env_file: Path | None = None):
        self._env_file = env_file

    @property
    def env_file(self) -> Path:
        if self._env_file is None:
            env_file = Path(os.environ.get("SWE_AGENT_ENV_FILE", "/root/.swe-agent-env"))
        else:
            env_file = self._env_file
        if not env_file.exists():
            env_file.write_text("{}")
        return env_file

    def __getitem__(self, key: str) -> str:
        return json.loads(self.env_file.read_text())[key]

    def get(self, key: str, default_value: Any = None) -> Any:
        return json.loads(self.env_file.read_text()).get(key, default_value)

    def __setitem__(self, key: str, value: Any):
        env = json.loads(self.env_file.read_text())
        env[key] = value
        self.env_file.write_text(json.dumps(env))


registry = EnvRegistry()


def get_current_file():
    return Path(registry["CURRENT_FILE"])  # type: ignore


def get_current_line():
    return int(registry["CURRENT_LINE"])  # type: ignore


def get_current_file_with_line_range(file_path: str | PurePath | None = None) -> tuple[Path, int, int]:
    """Returns 0-based index of the first and last line to print."""
    if file_path is None:
        _spec = registry["CURRENT_FILE"]
        assert _spec, "CURRENT_FILE is not set"
        file_path = Path(_spec)
    else:
        file_path = Path(file_path)
    current_line = int(registry["CURRENT_LINE"])  # type: ignore
    window = int(registry["WINDOW"])  # type: ignore
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
