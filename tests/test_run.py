import subprocess

def test_run_cli_help():
    args = [
        "python",
        "run.py",
        "--help",
    ]
    subprocess.run(args, check=True)


def test_run_obsolete():
    ...