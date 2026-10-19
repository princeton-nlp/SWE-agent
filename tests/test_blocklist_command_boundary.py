from __future__ import annotations

from sweagent.tools.tools import ToolConfig, ToolHandler


def _handler() -> ToolHandler:
    return ToolHandler(ToolConfig())


def test_vi_blocks_vi_but_not_view_image():
    handler = _handler()
    assert handler.should_block_action("vi file.txt")
    assert handler.should_block_action("vim file.txt")
    assert not handler.should_block_action("view_image screenshot.png")


def test_multiword_blocklist_entries_still_match_their_arguments():
    handler = _handler()
    assert handler.should_block_action("tail -f log.txt")
    assert not handler.should_block_action("tail log.txt")
    assert handler.should_block_action("python -m venv .venv")
    assert not handler.should_block_action("python -m pip install .")


def test_exact_standalone_commands_stay_blocked():
    handler = _handler()
    assert handler.should_block_action("python")
    assert handler.should_block_action("bash")
    assert not handler.should_block_action("python -c 'print(1)'")
