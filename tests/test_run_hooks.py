import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from sweagent.agent.problem_statement import GithubIssue, TextProblemStatement
from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
from sweagent.run.hooks.open_pr import OpenPRConfig, OpenPRHook
from sweagent.run.hooks.swe_bench_evaluate import SweBenchEvaluate
from sweagent.types import AgentRunResult


@pytest.fixture
def open_pr_hook_init_for_sop():
    hook = OpenPRHook(config=OpenPRConfig(skip_if_commits_reference_issue=True))
    hook._token = os.environ.get("GITHUB_TOKEN", "")
    hook._problem_statement = GithubIssue(github_url="https://github.com/swe-agent/test-repo/issues/1")
    return hook


@pytest.fixture
def agent_run_result():
    return AgentRunResult(
        info={
            "submission": "asdf",
            "exit_status": "submitted",
        },
        trajectory=[],
    )


def test_should_open_pr_fail_submission(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    agent_run_result.info["submission"] = None
    assert not hook.should_open_pr(agent_run_result)


def test_should_open_pr_fail_exit(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    agent_run_result.info["exit_status"] = "fail"
    assert not hook.should_open_pr(agent_run_result)


def test_should_open_pr_fail_invalid_url(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    agent_run_result.info["data_path"] = "asdf"
    assert not hook.should_open_pr(agent_run_result)


def test_should_open_pr_fail_closed(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    hook._problem_statement = GithubIssue(github_url="https://github.com/swe-agent/test-repo/issues/16")
    assert not hook.should_open_pr(agent_run_result)


def test_should_open_pr_fail_assigned(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    hook._problem_statement = GithubIssue(github_url="https://github.com/swe-agent/test-repo/issues/17")
    assert not hook.should_open_pr(agent_run_result)


def test_should_open_pr_fail_locked(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    hook._problem_statement = GithubIssue(github_url="https://github.com/swe-agent/test-repo/issues/18")
    assert not hook.should_open_pr(agent_run_result)


def test_should_open_pr_fail_has_pr(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    hook._problem_statement = GithubIssue(github_url="https://github.com/swe-agent/test-repo/issues/19")
    assert not hook.should_open_pr(agent_run_result)


def test_should_open_pr_success_has_pr_override(open_pr_hook_init_for_sop, agent_run_result):
    hook = open_pr_hook_init_for_sop
    hook._problem_statement = GithubIssue(github_url="https://github.com/swe-agent/test-repo/issues/19")
    hook._config.skip_if_commits_reference_issue = False
    assert hook.should_open_pr(agent_run_result)


def test_save_apply_patch_hook_concurrent_workers_save_to_correct_dirs(tmp_path):
    """Regression test for #1284: concurrent workers must not overwrite each
    other's per-instance state (_problem_statement, _env) in SaveApplyPatchHook.

    Before the fix, a single shared hook instance stored _problem_statement as a
    plain instance attribute.  When two workers both called on_instance_start()
    before either finished, the second write overwrote the first, causing both
    workers to save their patch into the same (wrong) output directory.

    The fix uses threading.local() so every worker thread sees its own copy.
    """
    hook = SaveApplyPatchHook(show_success_message=False)
    hook._output_dir = tmp_path

    # Barrier ensures both workers have called on_instance_start before either
    # proceeds to on_instance_completed, making the race window deterministic.
    barrier = threading.Barrier(2)

    def worker(instance_id: str, patch_content: str) -> None:
        ps = TextProblemStatement(text=f"Issue for {instance_id}", id=instance_id)
        env = MagicMock()
        env.repo = None  # skip apply_patch_locally path

        hook.on_instance_start(index=0, env=env, problem_statement=ps)

        # Hold here until both threads have written their problem_statement so
        # that the race window is guaranteed to be open.
        barrier.wait()

        result = AgentRunResult(
            info={"submission": patch_content, "exit_status": "submitted"},
            trajectory=[],
        )
        hook.on_instance_completed(result=result)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(worker, "instance-A", "patch A content")
        fb = pool.submit(worker, "instance-B", "patch B content")
        fa.result()
        fb.result()

    patch_a = tmp_path / "instance-A" / "instance-A.patch"
    patch_b = tmp_path / "instance-B" / "instance-B.patch"

    assert patch_a.exists(), "Patch for instance-A was not saved to its own directory"
    assert patch_b.exists(), "Patch for instance-B was not saved to its own directory"
    assert patch_a.read_text() == "patch A content"
    assert patch_b.read_text() == "patch B content"


@pytest.mark.parametrize(
    ("subset", "expected"),
    [
        ("lite", "swe-bench_lite"),
        ("verified", "swe-bench_verified"),
        ("multimodal", "swe-bench-m"),
    ],
)
def test_swe_bench_evaluate_subset_matches_sb_cli(tmp_path, subset, expected):
    """The subset passed to sb-cli must be one of its accepted values.

    sb-cli's ``Subset`` enum only accepts ``swe-bench_lite``, ``swe-bench_verified``
    and ``swe-bench-m``. In particular the multimodal dataset is ``swe-bench-m``,
    not ``swe-bench_multimodal``, so submitting the latter is rejected at the CLI
    boundary and ``--evaluate=True`` fails on a multimodal run.
    """
    hook = SweBenchEvaluate(output_dir=tmp_path, subset=subset, split="dev")
    call = hook._get_sb_call(tmp_path / "preds.json")
    # ["sb-cli", "submit", <subset>, <split>, ...]
    assert call[2] == expected


@pytest.mark.parametrize("subset", ["full", "multilingual"])
def test_swe_bench_evaluate_unsupported_subset_raises_value_error(tmp_path, subset):
    """Subsets with no sb-cli equivalent must fail with a clear error.

    ``full`` and ``multilingual`` are valid ``SWEBenchInstances.subset`` values for
    loading instances, but sb-cli cannot evaluate them. Building the call must raise
    a descriptive ValueError instead of a bare KeyError.
    """
    hook = SweBenchEvaluate(output_dir=tmp_path, subset=subset, split="dev")
    with pytest.raises(ValueError, match=subset):
        hook._get_sb_call(tmp_path / "preds.json")


class _LogCapture(logging.Handler):
    """Capture log records of a single logger (repo loggers do not propagate to the root logger)."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _install_fake_sb_cli(monkeypatch, tmp_path, script: str) -> None:
    """Install a fake ``sb-cli`` executable that shadows the real one on ``PATH``."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sb_cli = bin_dir / "sb-cli"
    sb_cli.write_text(script)
    sb_cli.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


def _make_evaluate_hook_with_prediction(tmp_path) -> SweBenchEvaluate:
    (tmp_path / "inst-1").mkdir()
    (tmp_path / "inst-1" / "inst-1.pred").write_text(
        json.dumps({"instance_id": "inst-1", "model_patch": "diff --git a/f b/f"})
    )
    hook = SweBenchEvaluate(output_dir=tmp_path, subset="lite", split="dev", continuous_submission_every=30)
    hook.last_evaluation_time = time.time() - 60
    return hook


def test_swe_bench_evaluate_reports_failed_background_submission(tmp_path, monkeypatch, agent_run_result):
    """Regression test: ``check_running_calls`` was never called from anywhere, so a
    continuous ``sb-cli submit`` call that failed was never reported.
    """
    _install_fake_sb_cli(
        monkeypatch,
        tmp_path,
        "#!/bin/bash\necho 'submission failed badly' >&2\nexit 1\n",
    )
    hook = _make_evaluate_hook_with_prediction(tmp_path)
    capture = _LogCapture()
    hook.logger.addHandler(capture)
    try:
        hook.on_instance_completed(result=agent_run_result)

        failed_logs = []
        for _ in range(50):
            # The next instance completion must report the failed submission
            hook.on_instance_completed(result=agent_run_result)
            failed_logs = [
                r
                for r in capture.records
                if r.levelno >= logging.ERROR and "Failed to submit results to SweBench eval" in r.getMessage()
            ]
            if failed_logs:
                break
            time.sleep(0.1)
    finally:
        hook.logger.removeHandler(capture)

    assert failed_logs, "failed sb-cli submission was never reported"
    assert "submission failed badly" in failed_logs[0].getMessage()
    assert not hook._running_calls, "finished call was never removed from the running calls"


def test_swe_bench_evaluate_background_submission_cannot_block_on_full_pipe(tmp_path, monkeypatch, agent_run_result):
    """Regression test: the pipes of the background ``sb-cli submit`` calls were never
    drained, so a verbose sb-cli writing more than the pipe buffer blocked forever and
    its predictions were silently never submitted.
    """
    marker = tmp_path / "sb-cli-finished"
    padding = "sb-cli progress line with a lot of padding so that the output exceeds the pipe buffer"
    _install_fake_sb_cli(
        monkeypatch,
        tmp_path,
        f'#!/bin/bash\nfor i in $(seq 1 5000); do echo "{padding} $i" >&2; done\necho done > "{marker}"\nexit 0\n',
    )
    hook = _make_evaluate_hook_with_prediction(tmp_path)
    hook.on_instance_completed(result=agent_run_result)

    deadline = time.time() + 10
    while not marker.exists() and time.time() < deadline:
        time.sleep(0.1)
    assert marker.exists(), "sb-cli never finished writing its output (blocked on a full pipe?)"

    for _ in range(50):
        # The next instance completion must reap the finished submission
        hook.on_instance_completed(result=agent_run_result)
        if not hook._running_calls:
            break
        time.sleep(0.1)
    assert not hook._running_calls, "finished call was never removed from the running calls"


def test_swe_bench_evaluate_on_end_reports_failed_background_submission(tmp_path, monkeypatch, agent_run_result):
    """Regression test: a continuous submission that fails right before the run ends
    must be reported by ``on_end``, the last lifecycle hook that runs.
    """
    _install_fake_sb_cli(
        monkeypatch,
        tmp_path,
        "#!/bin/bash\n"
        'if [[ "$*" == *"--wait_for_evaluation"* ]]; then\n'
        "  echo 'submission failed badly' >&2\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n",
    )
    hook = _make_evaluate_hook_with_prediction(tmp_path)
    capture = _LogCapture()
    hook.logger.addHandler(capture)
    try:
        hook.on_instance_completed(result=agent_run_result)

        failed_logs = []
        for _ in range(50):
            # on_end must report the failed background submission before the final one
            hook.on_end()
            failed_logs = [
                r
                for r in capture.records
                if r.levelno >= logging.ERROR and "Failed to submit results to SweBench eval" in r.getMessage()
            ]
            if failed_logs:
                break
            time.sleep(0.1)
    finally:
        hook.logger.removeHandler(capture)

    assert failed_logs, "failed sb-cli submission was never reported"
    assert "submission failed badly" in failed_logs[0].getMessage()
    assert not hook._running_calls, "finished call was never removed from the running calls"
