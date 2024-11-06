from __future__ import annotations

import pytest

from sweagent.tools.commands import Command
from sweagent.tools.parsing import (
    ActionParser,
    EditFormat,
    FormatError,
    Identity,
    JsonParser,
    ThoughtActionParser,
    XMLThoughtActionParser,
)


def test_action_parser():
    parser = ActionParser()
    command = Command(code="ls", name="ls")
    thought, action = parser("ls -l", [command])
    assert thought == "ls -l"
    assert action == "ls -l"
    with pytest.raises(FormatError):
        parser("invalid command", [command])


def test_thought_action_parser():
    parser = ThoughtActionParser()
    model_response = "Let's look at the files in the current directory.\n```\nls -l\n```"
    thought, action = parser(model_response, [])
    assert thought == "Let's look at the files in the current directory.\n"
    assert action == "ls -l\n"
    with pytest.raises(FormatError):
        parser("No code block", [])


def test_xml_thought_action_parser():
    parser = XMLThoughtActionParser()
    model_response = "Let's look at the files in the current directory.\n<command>\nls -l\n</command>"
    thought, action = parser(model_response, [])
    assert thought == "Let's look at the files in the current directory."
    assert action == "ls -l"
    with pytest.raises(FormatError):
        parser("No command tags", [])


def test_edit_format_parser():
    parser = EditFormat()
    model_response = "Let's replace the contents.\n```\nimport os\nos.listdir()\n```"
    thought, action = parser(model_response, [])
    assert thought == "Let's replace the contents.\n"
    assert action == "import os\nos.listdir()\n"
    with pytest.raises(FormatError):
        parser("No code block", [])


def test_identity_parser():
    parser = Identity()
    model_response = "Return as is"
    thought, action = parser(model_response, [])
    assert thought == model_response
    assert action == model_response


def test_json_parser():
    parser = JsonParser()
    model_response = '{"thought": "List files", "command": {"name": "ls", "arguments": {"path": "."}}}'
    thought, action = parser(model_response, [])
    assert thought == "List files"
    assert action == "ls ."

    invalid_json = "Not a JSON"
    with pytest.raises(FormatError):
        parser(invalid_json, [])

    missing_keys = '{"thought": "Missing command key"}'
    with pytest.raises(FormatError):
        parser(missing_keys, [])
