from statistics import mean
from swebench.metrics.constants import (
    FAIL_TO_PASS,
    PASS_TO_PASS,
    ResolvedStatus,
)


def compute_fail_to_pass(report: dict) -> float:
    """
    Compute fail-to-pass metric. Accepts single report as argument.
    """
    total = len(report[FAIL_TO_PASS]["success"]) + len(report[FAIL_TO_PASS]["failure"])
    if total == 0:
        return 1
    return len(report[FAIL_TO_PASS]["success"]) / total


def compute_pass_to_pass(report: dict) -> float:
    """
    Compute pass-to-pass metric. Accepts single report as argument.
    """
    total = len(report[PASS_TO_PASS]["success"]) + len(report[PASS_TO_PASS]["failure"])
    if total == 0:
        # TODO: Don't factor in p2p metrics
        return 1
    return len(report[PASS_TO_PASS]["success"]) / total


def compute_fail_to_pass_unweighted(reports: list[dict]) -> float:
    """
    Compute unweighted fail-to-pass metric. Accepts list of reports as argument.
    """
    if len(reports) == 0:
        return 0
    return mean([compute_fail_to_pass(r) for r in reports])


def compute_pass_to_pass_unweighted(reports: list[dict]) -> float:
    """
    Compute unweighted pass-to-pass metric. Accepts list of reports as argument.
    """
    if len(reports) == 0:
        return 0
    return mean([compute_pass_to_pass(r) for r in reports])


def compute_fail_to_pass_weighted(reports: list[dict]) -> float:
    """
    Compute weighted fail-to-pass metric. Accepts list of reports as argument.
    """
    report_all = {
        FAIL_TO_PASS: {
            "success": [x for r in reports for x in r[FAIL_TO_PASS]["success"]],
            "failure": [x for r in reports for x in r[FAIL_TO_PASS]["failure"]],
        },
    }
    return compute_fail_to_pass(report_all)


def compute_pass_to_pass_weighted(reports: list[dict]) -> float:
    """
    Compute weighted pass-to-pass metric. Accepts list of reports as argument.
    """
    report_all = {
        PASS_TO_PASS: {
            "success": [x for r in reports for x in r[PASS_TO_PASS]["success"]],
            "failure": [x for r in reports for x in r[PASS_TO_PASS]["failure"]],
        },
    }
    return compute_pass_to_pass(report_all)


def get_resolution_status(report: dict) -> str:
    """
    Determine resolved status of an evaluation instance

    Criteria:
        - If fail-to-pass (Resolution) = 1 and pass-to-pass (Maintenance) = 1 -> FULL
        - If (fail-to-pass (Resolution) < 1 and > 0) and pass-to-pass (Maintenance) = 1 -> PARTIAL
        - Otherwise -> NO
    """
    f2p = compute_fail_to_pass(report)
    p2p = compute_pass_to_pass(report)

    if f2p == 1 and p2p == 1:
        return ResolvedStatus.FULL.value
    elif f2p < 1 and f2p > 0 and p2p == 1:
        return ResolvedStatus.PARTIAL.value
    else:
        return ResolvedStatus.NO.value
