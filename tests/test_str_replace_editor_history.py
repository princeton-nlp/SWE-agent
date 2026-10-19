"""undo_edit has to survive a new process, because each tool call is one."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EDITOR = _REPO_ROOT / "tools" / "edit_anthropic" / "bin" / "str_replace_editor"
_REGISTRY_LIB = _REPO_ROOT / "tools" / "registry" / "lib"


def _run(env_file: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["SWE_AGENT_ENV_FILE"] = str(env_file)
    env["PYTHONPATH"] = str(_REGISTRY_LIB)
    env.pop("USE_LINTER", None)
    env.pop("USE_FILEMAP", None)
    return subprocess.run(
        [sys.executable, str(_EDITOR), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_undo_edit_restores_content_from_a_new_process(tmp_path):
    env_file = tmp_path / "env.json"
    env_file.write_text("{}")
    target = tmp_path / "sample.py"
    target.write_text("print(1)\n")

    replaced = _run(env_file, "str_replace", str(target), "--old_str", "print(1)", "--new_str", "print(2)")
    assert replaced.returncode == 0, replaced.stderr
    assert target.read_text() == "print(2)\n"
    stored = json.loads(json.loads(env_file.read_text())["file_history"])
    assert stored[str(target)] == ["print(1)\n"]

    undone = _run(env_file, "undo_edit", str(target))
    assert undone.returncode == 0, undone.stdout + undone.stderr
    assert target.read_text() == "print(1)\n"


def test_undo_edit_walks_back_through_each_edit(tmp_path):
    env_file = tmp_path / "env.json"
    env_file.write_text("{}")
    target = tmp_path / "sample.py"
    target.write_text("a\n")

    assert _run(env_file, "str_replace", str(target), "--old_str", "a", "--new_str", "b").returncode == 0
    assert _run(env_file, "str_replace", str(target), "--old_str", "b", "--new_str", "c").returncode == 0
    assert target.read_text() == "c\n"

    assert _run(env_file, "undo_edit", str(target)).returncode == 0
    assert target.read_text() == "b\n"
    assert _run(env_file, "undo_edit", str(target)).returncode == 0
    assert target.read_text() == "a\n"

    exhausted = _run(env_file, "undo_edit", str(target))
    assert exhausted.returncode == 18
