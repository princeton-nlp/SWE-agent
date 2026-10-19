"""Submissions must drop an applied /root/test.patch, same as tools/submit."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

from sweagent.agent.agents import autosubmission_diff_command

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SUBMIT_PATH = _REPO_ROOT / "tools" / "review_on_submit_m" / "bin" / "submit"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout


def _init_repo(path: Path) -> None:
    path.mkdir()
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "test")
    (path / "fix.py").write_text("base\n")
    (path / "test_fix.py").write_text("base\n")
    _git(path, "add", "fix.py", "test_fix.py")
    _git(path, "commit", "-m", "base")


def _load_submit():
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "registry" / "lib"))
    loader = importlib.machinery.SourceFileLoader("review_submit_under_test", str(_SUBMIT_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_review_submit_drops_applied_test_patch(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "test_fix.py").write_text("base\ngold\n")
    test_patch = tmp_path / "test.patch"
    test_patch.write_text(_git(repo, "diff", "--", "test_fix.py"))
    (repo / "fix.py").write_text("base\nfixed\n")

    model_patch = tmp_path / "model.patch"
    patch = _load_submit().write_submission_patch(repo, model_patch, test_patch)

    assert "fix.py" in patch
    assert "fixed" in patch
    assert "test_fix.py" not in patch
    assert "gold" not in patch
    assert (repo / "test_fix.py").read_text() == "base\n"


def test_review_submit_keeps_model_changes_when_there_is_no_test_patch(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "fix.py").write_text("base\nfixed\n")
    model_patch = tmp_path / "model.patch"
    patch = _load_submit().write_submission_patch(repo, model_patch, tmp_path / "missing.patch")
    assert "fix.py" in patch
    assert "fixed" in patch


def test_autosubmission_command_drops_applied_test_patch(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "test_fix.py").write_text("base\ngold\n")
    test_patch = tmp_path / "test.patch"
    test_patch.write_text(_git(repo, "diff", "--", "test_fix.py"))
    (repo / "fix.py").write_text("base\nfixed\n")
    model_patch = tmp_path / "model.patch"

    command = autosubmission_diff_command(test_patch=str(test_patch), model_patch=str(model_patch))
    subprocess.run(["bash", "-lc", command], cwd=repo, check=True)
    patch = model_patch.read_text()
    assert "fix.py" in patch
    assert "fixed" in patch
    assert "test_fix.py" not in patch
    assert "gold" not in patch
