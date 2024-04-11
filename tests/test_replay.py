import subprocess
from run_replay import get_args, main
import pytest

@pytest.mark.slow
def test_model_replay():
    # fixme: might make sure that path to test data is independent of CWD
    args = [
        "--traj_path",
        "tests/test_data/trajectories/gpt4__klieret__swe-agent-test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1/klieret__swe-agent-test-repo-i1.traj",
        "--data_path",
        "https://github.com/klieret/swe-agent-test-repo/issues/1",
        "--config_file",
        "config/default_from_url.yaml",
        "--raise_exceptions=True",
    ]
    args, remaining_args = get_args(args)
    main(**vars(args), forward_args=remaining_args)


def test_run_cli_help():
    args = [
        "python",
        "run_replay.py",
        "--help",
    ]
    subprocess.run(args, check=True)


@pytest.mark.slow
def test_model_replay_local_repo(tmp_path):
    local_repo_path = tmp_path / "swe-agent-test-repo"
    clone_cmd = ["git", "clone", "https://github.com/klieret/swe-agent-test-repo", local_repo_path]
    subprocess.run(clone_cmd, check=True)
    assert local_repo_path.is_dir()
    problem_statement_path = local_repo_path / "problem_statements" / "1.md"
    assert problem_statement_path.is_file()
    # fixme: Make path dynamic
    run_cmd = [
        "--traj_path",
        "tests/test_data/trajectories/gpt4__swe-agent-test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1/6e44b9__sweagenttestrepo-1c2844.traj",     
        "--data_path",
        str(local_repo_path),
        "--config_file",
        "config/default_from_url.yaml", 
        "--problem_statement",
        str(problem_statement_path),
    ]
    args, remaing_args = get_args(run_cmd)
    main(**vars(args), forward_args=remaing_args)