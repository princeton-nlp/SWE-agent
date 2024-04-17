import subprocess
import pytest

from run import OpenPRHook

def test_run_cli_help():
    args = [
        "python",
        "run.py",
        "--help",
    ]
    subprocess.run(args, check=True)



@pytest.fixture
def open_pr_hook_init_for_sop():
    hook = OpenPRHook()
    hook._token = ""
    hook._env = None
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/1"
    hook._open_pr = True
    hook._skip_if_commits_reference_issue = True
    return hook


@pytest.fixture
def info_dict():
    return {
        "submission": "asdf",
        "exit_status": "submitted",
    }


def test_should_open_pr_succeeds(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    assert hook.should_open_pr(info_dict)


def test_should_open_pr_fail_submission(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    info_dict["submission"] = None
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_exit(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    info_dict["exit_status"] = "fail"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_invalid_url(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "asdf"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_closed(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/16"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_assigned(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/17"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_fail_locked(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/18"
    assert not hook.should_open_pr(info_dict)

def test_should_open_pr_fail_has_pr(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/19"
    assert not hook.should_open_pr(info_dict)


def test_should_open_pr_success_has_pr_override(open_pr_hook_init_for_sop, info_dict):
    hook = open_pr_hook_init_for_sop
    hook._data_path = "https://github.com/klieret/swe-agent-test-repo/issues/19"
    hook._skip_if_commits_reference_issue = False
    assert hook.should_open_pr(info_dict)