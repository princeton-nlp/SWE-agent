import json
import os
from pathlib import Path
from typing import Any, Literal


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

    def get_if_none(self, value: Any, key: str, default_value: Any = None) -> Any:
        if value is not None:
            return value
        return self.get(key, default_value)

    def __setitem__(self, key: str, value: Any):
        env = json.loads(self.env_file.read_text())
        env[key] = value
        self.env_file.write_text(json.dumps(env))


registry = EnvRegistry()


class FileNotOpened(Exception):
    """Raised when no file is opened."""


class TextNotFound(Exception):
    """Raised when the text is not found in the window."""


class WindowedFile:
    def __init__(self, path: Path | None = None, *, current_line: int | None = None, window: int | None = None):
        """

        Convention: All line numbers are 0-indexed.
        """
        _path = registry.get_if_none(path, "CURRENT_FILE")
        if _path is None:
            raise FileNotOpened
        self.path = Path(_path)
        self.window = int(registry.get_if_none(window, "WINDOW"))
        self._current_line = 0
        # Ensure that we get a valid current line by using the setter
        self.current_line = int(
            registry.get_if_none(
                current_line,
                "CURRENT_LINE",
            )
        )

    @property
    def current_line(self) -> int:
        return self._current_line

    @current_line.setter
    def current_line(self, value: int):
        self._current_line = min(max(value, self.window // 2), self.n_lines - 1 - self.window // 2)
        registry["CURRENT_LINE"] = self.current_line

    @property
    def text(self) -> str:
        return self.path.read_text()

    @text.setter
    def text(self, new_text: str):
        self.path.write_text(new_text)

    @property
    def n_lines(self) -> int:
        return self.text.count("\n") + 1

    @property
    def line_range(self) -> tuple[int, int]:
        return (
            max(0, self.current_line - self.window // 2),
            min(self.current_line + (self.window - self.window // 2), self.n_lines),
        )

    def get_window_text(self) -> str:
        start_line, end_line = self.line_range
        return "\n".join(self.text.splitlines()[start_line:end_line])

    def set_window_text(self, new_text: str):
        """Set window text."""
        text = self.text.splitlines()
        start, stop = self.line_range
        text[start:stop] = new_text.splitlines()
        self.text = "\n".join(text)

    def replace_in_window(
        self,
        search: str,
        replace: str,
        *,
        reset_current_line: Literal["move_top", "keep"] = "move_top",
        n_replacements=1,
    ):
        """Search and replace in the window.

        Args:
            search: The string to search for (can be multi-line).
            replace: The string to replace it with (can be multi-line).
            reset_current_line: If set to "move_top", we set the current line to the 25%*window_size-th line of the new window.
                If set to "keep", we keep the current line.
            n_replacements: The number of replacements to make.
        """
        window_text = self.get_window_text()
        # Update line number
        index = window_text.find(search)
        if index == -1:
            raise TextNotFound
        # This line should now be the `25%*window_size`-th line of the new window
        window_start_line, _ = self.line_range
        replace_start_line = window_start_line + window_text[:index].count("\n")
        print("rsl", replace_start_line)
        new_window_text = window_text.replace(search, replace, n_replacements)
        self.set_window_text(new_window_text)
        if reset_current_line == "keep":
            pass
        elif reset_current_line == "move_top":
            # wstart = rstart - w//4
            # wend = wstart + w
            # c = (wend + wstart)//2 = (wstart + w + rstart - w//4)//2 = (rstart - w//4 + w + rstart - w//4)//2 = rstart + w//4
            self.current_line = replace_start_line + self.window // 4
        else:
            msg = f"Invalid value for reset_current_line: {reset_current_line}"
            raise ValueError(msg)

    def print_window(self):
        lines = self.path.read_text().splitlines()
        start_line, end_line = self.line_range
        print(f"[File: {self.path} ({len(lines)} lines total)]")
        if start_line > 0:
            print(f"({start_line} more lines above)")
        for i, line in enumerate(lines[start_line : end_line + 1]):
            print(f"{i+start_line+1}:{line}")
        if end_line < len(lines) - 1:
            print(f"({len(lines) - end_line - 1} more lines below)")

    def goto(self, line: int, mode: Literal["top", "exact"] = "top"):
        if mode == "exact":
            self.current_line = line
        elif mode == "top":
            # line is gonna be the 25%*window_size-th line of the new window
            self.current_line = line + self.window // 4
        else:
            raise NotImplementedError

    def scroll(self, n_lines: int):
        self.current_line += n_lines
