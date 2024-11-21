import json
import os
from pathlib import Path

from tests.utils import make_python_tool_importable

make_python_tool_importable("tools/defaults/lib/default_utils.py", "default_utils")
import default_utils  # type: ignore
from default_utils import (  # type: ignore
    get_current_file_with_line_range,
)


def test_env_file_override(with_tmp_env_file):
    assert Path(os.getenv("SWE_AGENT_ENV_FILE")).name == ".swe-agent-env"  # type: ignore


def test_get_current_file_with_line_range(with_tmp_env_file):
    default_utils.SWE_AGENT_ENV_FILE = with_tmp_env_file  # type: ignore
    test_path = with_tmp_env_file.parent.joinpath("test.py")
    registry = {
        "CURRENT_FILE": str(test_path),
        "CURRENT_LINE": "10",
        "WINDOW": "10",
    }
    with_tmp_env_file.write_text(json.dumps(registry))
    test_path.write_text("\n".join(map(str, range(20))))
    file_path, start_line, end_line = get_current_file_with_line_range()
    print(file_path, start_line, end_line)
    assert file_path == test_path
    assert start_line == 4
    assert end_line == 14
