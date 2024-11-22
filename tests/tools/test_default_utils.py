import json
import os
from pathlib import Path

import pytest

from tests.utils import make_python_tool_importable

make_python_tool_importable("tools/defaults/lib/default_utils.py", "default_utils")
import default_utils  # type: ignore


def test_env_file_override(with_tmp_env_file):
    assert Path(os.getenv("SWE_AGENT_ENV_FILE")).name == ".swe-agent-env"  # type: ignore


@pytest.fixture
def windowed_file(with_tmp_env_file):
    test_path = with_tmp_env_file.parent.joinpath("test.py")
    registry = {
        "CURRENT_FILE": str(test_path),
        "CURRENT_LINE": "10",
        "WINDOW": "10",
    }
    with_tmp_env_file.write_text(json.dumps(registry))
    test_path.write_text("\n".join(map(str, range(100))))
    return default_utils.WindowedFile()


def test_windowed_file(windowed_file):
    wfile = windowed_file
    assert wfile.current_line == 10
    assert wfile.window == 10
    assert wfile.n_lines == 100
    a, b = wfile.line_range
    assert b - a == wfile.window
    assert wfile.line_range == (5, 15)
    wfile.print_window()
    wfile.replace_in_window("10", "Hello, world!")
    assert wfile.n_lines == 100
    assert wfile.line_range == (7, 17)
    wfile.current_line = 50
    wfile.print_window()
    wfile.replace_in_window("50", "Hello, world!")
    wfile.print_window()
    # Line 50 is now the 2nd line of the new window
    print(wfile.current_line)
    assert wfile.line_range == (47, 57)


def test_windowed_file_goto(windowed_file):
    wfile = windowed_file
    assert wfile.current_line == 10
    wfile.goto(0, mode="top")
    assert wfile.line_range[0] == 0
    wfile.goto(50, mode="top")
    # first line is 50 - 10//4 = 47
    assert wfile.line_range[0] == 47
    wfile.goto(50, mode="exact")
    assert wfile.current_line == 50


def test_windowed_file_scroll(windowed_file):
    wfile = windowed_file
    assert wfile.current_line == 10
    wfile.scroll(10)
    assert wfile.current_line == 20
    wfile.scroll(-10)
    assert wfile.current_line == 10
    wfile.scroll(-100)
    # Can't go lower than the middle of the lowest window
    assert wfile.current_line == 5
