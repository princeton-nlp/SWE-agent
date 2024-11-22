import json
import os
from pathlib import Path

import pytest

from sweagent import TOOLS_DIR
from tests.utils import make_python_tool_importable

DEFAULT_TOOLS_DIR = TOOLS_DIR / "defaults"
DEFAULT_TOOLS_BIN = DEFAULT_TOOLS_DIR / "bin"

make_python_tool_importable(DEFAULT_TOOLS_DIR / "lib/default_utils.py", "default_utils")
import default_utils  # type: ignore


def test_env_file_override(with_tmp_env_file):
    assert Path(os.getenv("SWE_AGENT_ENV_FILE")).name == ".swe-agent-env"  # type: ignore


@pytest.fixture
def windowed_file(with_tmp_env_file):
    test_path = with_tmp_env_file.parent.joinpath("test.py")
    registry = {
        "CURRENT_FILE": str(test_path),
        "FIRST_LINE": "10",
        "WINDOW": "10",
    }
    with_tmp_env_file.write_text(json.dumps(registry))
    test_path.write_text("\n".join(map(str, range(100))))
    wf = default_utils.WindowedFile(exit_on_exception=False)
    wf.offset_multiplier = 1 / 4
    return wf


def test_windowed_file(windowed_file):
    wfile = windowed_file
    assert wfile.first_line == 10
    assert wfile.window == 10
    assert wfile.n_lines == 100
    a, b = wfile.line_range
    assert b - a == wfile.window
    assert wfile.line_range == (10, 20)
    wfile.print_window()
    wfile.replace_in_window("10", "Hello, world!")
    assert wfile.n_lines == 100
    assert wfile.line_range == (7, 17)
    wfile.first_line = 50
    wfile.print_window()
    wfile.replace_in_window("50", "Hello, world!")
    wfile.print_window()
    # Line 50 is now the 2nd line of the new window
    assert wfile.line_range == (47, 57)
    with pytest.raises(default_utils.TextNotFound):
        wfile.replace_in_window("asdf", "Hello, world!")


def test_windowed_file_goto(windowed_file):
    wfile = windowed_file
    assert wfile.first_line == 10
    wfile.goto(0, mode="top")
    assert wfile.line_range[0] == 0
    wfile.goto(50, mode="top")
    # first line is 50 - 10//4 = 47
    assert wfile.line_range[0] == 47


def test_windowed_file_scroll(windowed_file):
    wfile = windowed_file
    assert wfile.first_line == 10
    wfile.scroll(10)
    assert wfile.first_line == 20
    wfile.scroll(-10)
    assert wfile.first_line == 10
    wfile.scroll(-100)
    # Can't go lower than the middle of the lowest window
    assert wfile.first_line == 0


# def test_goto_command(windowed_file):
#     wfile = windowed_file
#     assert wfile.current_line == 10
#     assert (DEFAULT_TOOLS_BIN / "goto").exists()

#     # Use sys.executable to get the correct Python interpreter
#     import sys
#     cmd = f"{sys.executable} {DEFAULT_TOOLS_BIN}/goto 50"
#     print(
#         subprocess.check_output(
#             cmd,
#             shell=True,
#             universal_newlines=True,
#             stderr=subprocess.STDOUT,
#             env=os.environ.copy(),  # Ensure we pass the current environment
#         )
#     )
#     assert wfile.current_line == 50


_DEFAULT_WINDOW_OUTPUT = """[File: {path} (100 lines total)]
(10 more lines above)
11:10
12:11
13:12
14:13
15:14
16:15
17:16
18:17
19:18
20:19
21:20
(79 more lines below)
"""


def test_print_window(windowed_file, capsys):
    wfile = windowed_file
    wfile.print_window()
    captured = capsys.readouterr()
    print(captured.out)
    expected = _DEFAULT_WINDOW_OUTPUT.format(path=wfile.path.resolve())
    assert captured.out == expected


_DEFAULT_WINDOW_OUTPUT_NEW_FILE = """[File: {path} (1 lines total)]
1:
"""


def test_print_window_new_file(with_tmp_env_file, capsys):
    test_path = with_tmp_env_file.parent.joinpath("new_test.py")
    registry = {
        "CURRENT_FILE": str(test_path),
        "FIRST_LINE": "10",
        "WINDOW": "10",
    }
    with_tmp_env_file.write_text(json.dumps(registry))
    new_file = with_tmp_env_file.parent.joinpath(registry["CURRENT_FILE"])
    new_file.write_text("\n")
    wfile = default_utils.WindowedFile()
    wfile.print_window()
    captured = capsys.readouterr()
    print(captured.out)
    expected = _DEFAULT_WINDOW_OUTPUT_NEW_FILE.format(path=new_file.resolve())
    assert captured.out == expected
