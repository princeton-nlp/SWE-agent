from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from run_replay import get_args, main
from sweagent import CONFIG_DIR


@pytest.fixture
def swe_agent_test_repo_clone(tmp_path):
    local_repo_path = tmp_path / "test-repo"
    clone_cmd = ["git", "clone", "https://github.com/swe-agent/test-repo", local_repo_path]
    subprocess.run(clone_cmd, check=True)
    return local_repo_path


@pytest.fixture
def swe_agent_test_repo_traj(test_trajectories_path) -> Path:
    p = (
        test_trajectories_path
        / "gpt4__swe-agent-test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1"
        / "6e44b9__sweagenttestrepo-1c2844.traj"
    )
    assert p.is_file()
    return p


@pytest.fixture
def swe_agent_test_repo_local_problem_stmt(swe_agent_test_repo_clone) -> Path:
    problem_stmt = swe_agent_test_repo_clone / "problem_statements" / "1.md"
    assert problem_stmt.is_file()
    return problem_stmt


@pytest.mark.slow
@pytest.mark.parametrize("problem_statement_source", ["github", "local"])
def test_model_replay_github_repo(
    tmpdir,
    swe_agent_test_repo_traj,
    problem_statement_source,
    swe_agent_test_repo_local_problem_stmt,
):
    if problem_statement_source == "github":
        data_path = "https://github.com/swe-agent/test-repo/issues/1"
    elif problem_statement_source == "local":
        data_path = str(swe_agent_test_repo_local_problem_stmt)
    args = [
        "--traj_path",
        str(swe_agent_test_repo_traj.resolve()),
        "--data_path",
        data_path,
        "--config_file",
        str(CONFIG_DIR / "default_from_url.yaml"),
        "--raise_exceptions",
    ]
    if problem_statement_source == "local":
        args.extend(["--repo_path", "https://github.com/swe-agent/test-repo/"])
    args, remaining_args = get_args(args)
    with tmpdir.as_cwd():
        # Test that we can run run.py also independently from repo dir
        main(**vars(args), forward_args=remaining_args)


@pytest.mark.slow
def test_model_replay_from_json(test_trajectories_path, test_data_sources_path):
    traj_path = (
        test_trajectories_path
        / "gpt4__swe-bench-dev-easy_first_only__default__t-0.00__p-0.95__c-3.00__install-1"
        / "pydicom__pydicom-1458.traj"
    )
    assert traj_path.is_file()
    data_path = test_data_sources_path / "swe-bench-dev-easy_first_only.json"
    assert data_path.is_file()
    args = [
        "--traj_path",
        str(traj_path),
        "--data_path",
        str(data_path),
        "--config_file",
        "config/default.yaml",
        "--raise_exceptions",
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
@pytest.mark.parametrize("problem_statement_source", ["github", "local"])
def test_model_replay_local_repo(swe_agent_test_repo_clone, swe_agent_test_repo_traj, problem_statement_source):
    local_repo_path = swe_agent_test_repo_clone
    if problem_statement_source == "github":
        problem_statement_path = "https://github.com/swe-agent/test-repo/issues/1"
    elif problem_statement_source == "local":
        problem_statement_path = local_repo_path / "problem_statements" / "1.md"
        assert problem_statement_path.is_file()
    else:
        raise ValueError(problem_statement_source)
    run_cmd = [
        "--traj_path",
        str(swe_agent_test_repo_traj),
        "--repo_path",
        str(local_repo_path),
        "--config_file",
        "config/default_from_url.yaml",
        "--data_path",
        str(problem_statement_path),
        "--apply_patch",
        "--raise_exceptions",
    ]
    print(run_cmd)
    args, remaining_args = get_args(run_cmd)
    main(**vars(args), forward_args=remaining_args)
    solution = (swe_agent_test_repo_traj.parent / "solution_missing_colon.py").read_text().strip()
    solution_retrieved = (local_repo_path / "tests" / "missing_colon.py").read_text().strip()
    assert solution == solution_retrieved


def test_exception_replay_local_dirty(swe_agent_test_repo_clone, swe_agent_test_repo_traj):
    """Test that swe-agent refuses to work if the local repo is dirty"""
    problem_statement_path = swe_agent_test_repo_clone / "problem_statements" / "1.md"
    test_file = swe_agent_test_repo_clone / "tests" / "missing_colon.py"
    assert test_file.is_file()
    test_file.write_text(test_file.read_text().replace("division", "division_function"))
    run_cmd = [
        "--traj_path",
        str(swe_agent_test_repo_traj),
        "--repo_path",
        str(swe_agent_test_repo_clone),
        "--config_file",
        "config/default_from_url.yaml",
        "--data_path",
        str(problem_statement_path),
        "--apply_patch",
        "--raise_exceptions",
    ]
    args, remaining_args = get_args(run_cmd)
    with pytest.raises(ValueError, match=".*dirty.*"):
        main(**vars(args), forward_args=remaining_args)
