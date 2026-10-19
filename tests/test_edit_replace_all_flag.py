"""``edit``'s optional replace-all flag must honor an explicit false."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

_EDITOR_PATH = Path(__file__).resolve().parents[1] / "tools" / "windowed_edit_replace" / "bin" / "edit"


def _load_editor():
    loader = importlib.machinery.SourceFileLoader("windowed_edit_under_test", str(_EDITOR_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def editor():
    return _load_editor()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
    ],
)
def test_parse_replace_all(editor, raw, expected):
    assert editor.parse_replace_all(raw) is expected


def test_omitted_replace_all_stays_false(editor):
    args = editor.get_parser().parse_args(["search", "replace"])
    assert args.replace_all is False


def test_explicit_false_argument_stays_false(editor):
    args = editor.get_parser().parse_args(["search", "replace", "false"])
    assert args.replace_all is False


def test_explicit_true_argument(editor):
    args = editor.get_parser().parse_args(["search", "replace", "true"])
    assert args.replace_all is True
