import glob
import os

from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    TESTS_TIMEOUT,
)
from swebench.metrics.getters import (
    log_path_to_sms,
    get_diffs,
    get_repo_from_lp,
)
from swebench.metrics.log_parsers import MAP_REPO_TO_PARSER
from typing import Tuple


def monitor_validation(
    path_to_logs: str, log_prefix: str = None
) -> Tuple[list, list, list, list]:
    """
    Check log files generated from a `check_instances` run to see how many instances were successfully
    installed and/or tested.

    Args:
        path_to_logs (str): path to log files
        log_prefix (str): prefix of log files
    Returns:
        failed_install (list): list of log files where instances failed to install
        corrupt_test_patch (list): list of log files where test patch was corrupt
        corrupt_patch (list): list of log files where patch was corrupt
        success (list): list of log files where instances were successfully installed and tested
    """
    failed_install = list()
    corrupt_test_patch = list()
    corrupt_patch = list()
    timeout = list()
    success = list()
    count = 0

    # Iterate through all logs with prefix in path_to_logs
    file_format = f"{log_prefix}*.log" if log_prefix else "*.log"
    for x in glob.glob(os.path.join(path_to_logs, file_format)):
        with open(x) as f:
            content = f.read()
            if any([x in content for x in [APPLY_PATCH_FAIL, APPLY_PATCH_PASS]]):
                # Count number of successful patch applies
                patch_applies = content.count(APPLY_PATCH_PASS)
                if TESTS_TIMEOUT in content:
                    # Running test timed out
                    timeout.append(x)
                elif patch_applies == 0:
                    # If none, then test patch was corrupt
                    corrupt_test_patch.append(x)
                elif patch_applies == 1:
                    # If one, then patch was corrupt
                    corrupt_patch.append(x)
                else:
                    # If both, then both test patch and patch were applied successfully
                    assert patch_applies == 2
                    success.append(x)
            else:
                # If no patch was applied, then installation failed
                failed_install.append(x)
            count += 1

    # Logging
    print(f"Total Attempts: {count}")
    print(f"Failed: {len(failed_install)}")
    print(f"Usable: {count - len(failed_install)}")
    print(f"Corrupt Test: {len(corrupt_test_patch)}")
    print(f"Corrupt Diff: {len(corrupt_patch)}")
    print(f"Test Script Timeout: {len(timeout)}")
    print(f"Success E2E: {len(success)}")

    # Check that all instances were accounted for
    assert (
        len(success)
        + len(corrupt_patch)
        + len(corrupt_test_patch)
        + len(failed_install)
        + len(timeout)
        == count
    )

    return failed_install, corrupt_test_patch, corrupt_patch, timeout, success


def monitor_logs_same_diff(log_dir: str, repo: str = None) -> Tuple[list, list]:
    """
    Given a log directory and repo, return a list of logs where pre-test
    and post-test logs are same/different

    Args:
        log_dir (str): path to log files
        repo (str): repo name
    Returns:
        logs_same: list of logs where post test behavior is same
        logs_diff: list of logs where post test behavior is different
    """
    logs_same, logs_diff = [], []

    # Find all log files for a repo in the given log directory
    file_format = f"{repo.split('/')[0]}*.log" if repo else "*.log"
    for log_fp in glob.glob(os.path.join(log_dir, file_format)):
        if repo:
            log_parser = MAP_REPO_TO_PARSER[repo]
        else:
            # Get repo from log file path
            repo = get_repo_from_lp(log_fp)
            log_parser = MAP_REPO_TO_PARSER[repo]

        sms, found = log_path_to_sms(log_fp, log_parser)
        if not found:
            continue
        sm_before, sm_after = sms[0], sms[1]

        # Get differences between pre, post patch behavior for log file
        diffs = get_diffs(sm_before, sm_after)
        if len(diffs) == 0:
            logs_same.append(log_fp)
        else:
            logs_diff.append((log_fp, diffs))

    return logs_same, logs_diff
