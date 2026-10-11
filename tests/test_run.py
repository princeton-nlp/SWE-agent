from __future__ import annotations

import subprocess

import pytest

from sweagent.run.run import get_cli, main


def test_run_cli_no_arg_error():
    args = [
        "sweagent",
    ]
    output = subprocess.run(args, check=False, capture_output=True)
    print(output.stdout.decode())
    print(output.stderr.decode())
    assert output.returncode in [1, 2]
    assert "run-batch" in output.stdout.decode()
    assert "run-replay" in output.stdout.decode()
    assert "run" in output.stdout.decode()


def test_run_cli_main_help():
    args = [
        "sweagent",
        "--help",
    ]
    output = subprocess.run(args, check=True, capture_output=True)
    assert "run-batch" in output.stdout.decode()
    assert "run-replay" in output.stdout.decode()
    assert "run" in output.stdout.decode()


def test_run_cli_subcommand_help():
    args = [
        "sweagent",
        "run",
        "--help",
    ]
    output = subprocess.run(args, check=True, capture_output=True)
    assert "--config" in output.stdout.decode()


def _get_cli_command_choices() -> list[str]:
    parser = get_cli()
    command_action = next(action for action in parser._actions if action.choices)
    return list(command_action.choices)


@pytest.mark.parametrize("command", _get_cli_command_choices())
def test_cli_subcommand_help_dispatches(command):
    """Check that every accepted subcommand dispatches to an existing module."""
    with pytest.raises(SystemExit):
        main([command, "--help"])
