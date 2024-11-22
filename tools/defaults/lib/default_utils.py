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
    def __init__(
        self,
        path: Path | None = None,
        *,
        first_line: int | None = None,
        window: int | None = None,
        exit_on_exception: bool = True,
    ):
        """

        Args:
            exit_on_exception: If False, will raise exception.
                If true, will print an error message and exit.

        Will create file if not found.

        Internal convention: All line numbers are 0-indexed.
        """
        _path = registry.get_if_none(path, "CURRENT_FILE")
        self._exit_on_exception = exit_on_exception
        if _path is None:
            if self._exit_on_exception:
                print("No file open. Use the open command first.")
                exit(1)
            raise FileNotOpened
        self.path = Path(_path)
        if self.path.is_dir():
            msg = f"Error: {self.path} is a directory. You can only open files. Use cd or ls to navigate directories."
            if self._exit_on_exception:
                print(msg)
                exit(1)
            raise IsADirectoryError(msg)
        if not self.path.exists():
            msg = f"File {self.path} not found"
            if self._exit_on_exception:
                print(msg)
                exit(1)
            raise FileNotFoundError(msg)
        registry["CURRENT_FILE"] = str(self.path.resolve())
        self.window = int(registry.get_if_none(window, "WINDOW"))
        self.overlap = int(registry.get("OVERLAP", 0))
        # Ensure that we get a valid current line by using the setter
        self.first_line = int(
            registry.get_if_none(
                first_line,
                "FIRST_LINE",
                0,
            )
        )
        self.offset_multiplier = 1 / 6

    @property
    def first_line(self) -> int:
        return self._first_line

    @first_line.setter
    def first_line(self, value: int | float):
        value = int(value)
        self._first_line = max(0, min(value, self.n_lines - 1 - self.window))
        registry["FIRST_LINE"] = self.first_line

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
        """Return current line +/- window/2.
        `line_range[1] - line_range[0] == window` as long as there are
        at least `window` lines in the file. `first_line` does the handling
        of making sure that we don't go out of bounds.
        """
        return self.first_line, self.first_line + self.window

    def get_window_text(self) -> str:
        start_line, end_line = self.line_range
        return "\n".join(self.text.splitlines()[start_line:end_line])

    def set_window_text(self, new_text: str) -> None:
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
        reset_first_line: Literal["top", "keep"] = "top",
        n_replacements=1,
    ) -> None:
        """Search and replace in the window.

        Args:
            search: The string to search for (can be multi-line).
            replace: The string to replace it with (can be multi-line).
            reset_first_line: If set to "keep", we keep the current line. Otherwise
                we `goto` the line where the replacement started with goto mode equal
                to this setting.
            n_replacements: The number of replacements to make.
        """
        window_text = self.get_window_text()
        # Update line number
        index = window_text.find(search)
        if index == -1:
            if self._exit_on_exception:
                print(f"Text not found: {search}")
                exit(1)
            raise TextNotFound
        # This line should now be the `25%*window_size`-th line of the new window
        window_start_line, _ = self.line_range
        replace_start_line = window_start_line + window_text[:index].count("\n")
        print("rsl", replace_start_line)
        new_window_text = window_text.replace(search, replace, n_replacements)
        self.set_window_text(new_window_text)
        if reset_first_line == "keep":
            pass
        else:
            self.goto(replace_start_line, mode=reset_first_line)

    def replace(self, search: str, replace: str, *, reset_first_line: Literal["top", "keep"] = "top"):
        index = self.text.find(search)
        if index == -1:
            if self._exit_on_exception:
                print(f"Text not found: {search}")
                exit(1)
            raise TextNotFound
        replace_start_line = self.text[:index].count("\n")
        new_text = self.text.replace(search, replace)
        self.text = new_text
        if reset_first_line == "keep":
            pass
        else:
            self.goto(replace_start_line, mode=reset_first_line)

    def print_window(self):
        lines = self.text.splitlines()
        start_line, end_line = self.line_range
        assert start_line >= 0, start_line
        print(f"[File: {self.path} ({len(lines)} lines total)]")
        if start_line > 0:
            print(f"({start_line} more lines above)")
        for i, line in enumerate(lines[start_line : end_line + 1]):
            print(f"{i+start_line+1}:{line}")
        if end_line < len(lines) - 1:
            print(f"({len(lines) - end_line - 1} more lines below)")

    def goto(self, line: int, mode: Literal["top"] = "top"):
        if mode == "top":
            self.first_line = line - self.window * self.offset_multiplier
        else:
            raise NotImplementedError

    def scroll(self, n_lines: int):
        if n_lines > 0:
            self.first_line += n_lines - self.overlap
        elif n_lines < 0:
            self.first_line += n_lines + self.overlap
