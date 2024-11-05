from __future__ import annotations

import subprocess


def test_run_cli_no_arg_error():
    args = [
        "sweagent",
    ]
    output = subprocess.run(args, check=False, capture_output=True)
    print(output.stdout.decode())
    print(output.stderr.decode())
    assert output.returncode == 2
    assert "run-batch" in output.stdout.decode()
    assert "run-replay" in output.stdout.decode()
    assert "run" in output.stdout.decode()


def test_run_cli_main_help():
    args = [
        "sweagent",
        "--help",
    ]
    output = subprocess.run(args, check=True, capture_output=True)
    assert output.returncode == 0
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
    assert output.returncode == 0
    assert "--config" in output.stdout.decode()
