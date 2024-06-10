import glob, json, os

from collections import Counter
from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    INSTALL_FAIL,
    KEY_INSTANCE_ID,
    RESET_FAILED,
    TESTS_ERROR,
    TESTS_TIMEOUT,
    PatchType,
)
from swebench.metrics.constants import (
    FAIL_TO_FAIL,
    FAIL_TO_PASS,
    PASS_TO_FAIL,
    PASS_TO_PASS,
)
from swebench.metrics.getters import (
    get_file_name_from_lp,
    get_logs_eval,
    get_id_from_lp,
    test_failed,
    test_passed,
    get_eval_refs,
)
from swebench.metrics.metrics import (
    compute_fail_to_pass_unweighted,
    compute_fail_to_pass_weighted,
    compute_pass_to_pass_unweighted,
    compute_pass_to_pass_weighted,
    get_resolution_status,
    ResolvedStatus,
)
from tqdm.auto import tqdm
from typing import Tuple


### MARK - Eval Report Generation


def get_eval_report(
    eval_sm: dict,
    gold_results: dict,
    calculate_to_fail: bool = False
) -> dict:
    """
    Create a report based on failure/pass change from gold results to eval results.

    Args:
        eval_sm (dict): evaluation status map
        gold_results (dict): gold results
        calculate_to_fail (bool): whether to calculate metrics for "x to fail" tests
    Returns:
        report (dict): report of metrics

    Metric Definitions (Gold Result Pair + Eval Result):
    - Fail-Pass (F2P) + P: Success (Resolution)
    - Pass-Pass (P2P) + P: Success (Maintenance)
    - Fail-Pass (F2P) + F: Failure
    - Pass-Pass (P2P) + F: Failure

    Miscellaneous Definitions
    - Fail-Fail (F2F) + F: Failure Maintenance
    - Pass-Fail (P2F) + F: Not considered
    - Fail-Fail (F2F) + P: Success (Extra Credit)
    - Pass-Fail (P2F) + P: Not considered
    """
    # Calculate resolution metrics
    f2p_success = []
    f2p_failure = []
    for test_case in gold_results[FAIL_TO_PASS]:
        if test_passed(test_case, eval_sm):
            # Assume silent success for now (test case not in eval_sm)
            f2p_success.append(test_case)
        elif test_failed(test_case, eval_sm):
            f2p_failure.append(test_case)

    # Calculate maintenance metrics
    p2p_success = []
    p2p_failure = []
    for test_case in gold_results[PASS_TO_PASS]:
        if test_passed(test_case, eval_sm):
            p2p_success.append(test_case)
        elif test_failed(test_case, eval_sm):
            p2p_failure.append(test_case)
    
    results = {
        FAIL_TO_PASS: {
            "success": f2p_success,
            "failure": f2p_failure,
        },
        PASS_TO_PASS: {
            "success": p2p_success,
            "failure": p2p_failure,
        }
    }

    f2f_success = []
    f2f_failure = []
    p2f_success = []
    p2f_failure = []
    if calculate_to_fail:
        # Calculate "extra credit" metrics
        for test_case in gold_results[FAIL_TO_FAIL]:
            if test_passed(test_case, eval_sm):
                f2f_success.append(test_case)
            elif test_failed(test_case, eval_sm):
                f2f_failure.append(test_case)

        # Calculate not considered metrics
        for test_case in gold_results[PASS_TO_FAIL]:
            if test_passed(test_case, eval_sm):
                p2f_success.append(test_case)
            elif test_failed(test_case, eval_sm):
                p2f_failure.append(test_case)

    results.update({
        FAIL_TO_FAIL: {
            "success": f2f_success,
            "failure": f2f_failure,
        },
        PASS_TO_FAIL: {
            "success": p2f_success,
            "failure": p2f_failure,
        }
    })
    return results


def get_eval_reports_for_logs(
    eval_logs: list,
    swe_bench_tasks: str,
    callback: callable = None,
    verbose: bool = False,
) -> Tuple[dict, dict]:
    """
    Wrapper for getting eval report for a list of evaluation log paths.

    Args:
        eval_logs (list): list of paths to evaluation logs
        swe_bench_tasks (str): path to eval task instances (swe-bench.json)
        callback (callable): callback function for evaluation logs
        verbose (bool): whether to print verbose output
    Returns:
        reports_patch_success (dict): dict of eval reports for patch apply successes
        reports_patch_failure (dict): dict of eval reports for patch apply failures
    """
    reports_patch_success = {}
    reports_patch_failure = {}
    eval_refs = get_eval_refs(swe_bench_tasks)

    for eval_log in eval_logs:
        # Remove task instances that do not satisfy callback
        if callback is not None and not callback(eval_log):
            continue

        # Get gold results
        instance_id = get_id_from_lp(eval_log)
        if instance_id not in eval_refs:
            if verbose:
                print(f"Gold results not found for {instance_id}")
            continue

        gold_results = eval_refs[instance_id]

        # Get eval logs
        eval_sm, has_report = get_logs_eval(eval_log)

        if not has_report:
            # If eval patch failed to apply, convert to report
            # format with tests as failures
            reports_patch_failure[get_file_name_from_lp(eval_log)] = {
                test_type: {"success": [], "failure": tests}
                for test_type, tests in gold_results.items()
            }
            continue

        # Compare eval status map and gold status map
        report = get_eval_report(eval_sm, gold_results)
        reports_patch_success[get_file_name_from_lp(eval_log)] = report

    return reports_patch_success, reports_patch_failure


def get_eval_reports_for_dir(
    eval_dir: str, swe_bench_tasks: str, callback: callable = None, verbose=False
) -> dict:
    """
    Wrapper for getting eval report for a directory of evaluation logs.

    Args:
        eval_dir (str): path to directory of evaluation logs
        (See get_eval_reports_for_logs for other args)
    """
    if not os.path.exists(eval_dir):
        raise ValueError(f"Path {eval_dir} does not exist")
    logs_list = [x for x in glob.glob(os.path.join(eval_dir, "*.log"))]
    return get_eval_reports_for_logs(logs_list, swe_bench_tasks, callback, verbose)


### MARK - Model Evaluation Summary


def get_model_eval_summary(
    predicts_path: str,
    eval_dir: str,
    swe_bench_tasks: str,
    repo: str = None,
) -> dict:
    """
    Generate a summary of model evaluation results.

    Args:
        predicts_path (str): path to predictions file
        eval_dir (str): path to directory of evaluation logs
        swe_bench_tasks (str): path to eval references (swe-bench-eval-refs.json)
        repo (str): if given, repo name to limit evaluation to
    """
    # Load Predictions
    preds = []
    with open(predicts_path) as f:
        for line in f.readlines():
            preds.append(json.loads(line))

    # Filter by repo if provided
    criteria_eval_sm = None
    if repo is not None:
        criteria_pred = lambda pred: repo in pred[KEY_INSTANCE_ID]
        criteria_eval_sm = lambda eval_log: repo in eval_log
        preds = [x for x in preds if criteria_pred(x)]

    # Get reports
    reports_patch_success, reports_patch_failure = get_eval_reports_for_dir(
        eval_dir, swe_bench_tasks, callback=criteria_eval_sm, verbose=False
    )

    # Print reports for different granularities of patch success/failure
    summary = {
        "repo": repo if repo is not None else "all",
        "total_predictions": len(preds),
    }
    reports_by_patch_status = [
        ("Patch Apply Success", [reports_patch_success]),
        (
            "Patch Apply Success + Failure",
            [reports_patch_success, reports_patch_failure],
        ),
    ]
    format_dec = lambda x: round(x * 100, 2)
    for report_by_patch_status in reports_by_patch_status:
        r = [list(x.values()) for x in report_by_patch_status[1]]
        r = [item for sublist in r for item in sublist]

        resolutions = Counter([get_resolution_status(_r) for _r in r])
        summary[report_by_patch_status[0]] = {
            "f2p_weighted": format_dec(compute_fail_to_pass_weighted(r)),
            "p2p_weighted": format_dec(compute_pass_to_pass_weighted(r)),
            "f2p_unweighted": format_dec(compute_fail_to_pass_unweighted(r)),
            "p2p_unweighted": format_dec(compute_pass_to_pass_unweighted(r)),
            "cases": report_by_patch_status[1],
            "case_resolution_counts": dict(resolutions),
            "case_resolution_rates": {
                k: round(v / len(r) * 100, 2) for k, v in resolutions.items()
            },
        }

    return summary


def get_model_report(
    model: str,
    predictions_path: str,
    swe_bench_tasks: str,
    log_dir: str,
    verbose: bool = False,
) -> dict:
    """
    Generate a report of model evaluation results from predictions, task instances,
    and evaluation logs.

    Args:
        model (str): model name
        predictions_path (str): path to predictions file
        swe_bench_tasks (str): path to eval references (swe-bench-eval-refs.json)
        log_dir (str): path to directory of evaluation logs
        verbose (bool): show tqdm to track progress
    Returns:
        report_map (dict): map of repo to report
    """
    eval_refs = get_eval_refs(swe_bench_tasks)
    for k, v in eval_refs.items():
        eval_refs[k] = {key: v[key] for key in [KEY_INSTANCE_ID, FAIL_TO_PASS, PASS_TO_PASS]}

    # Get predictions
    predictions = []
    if predictions_path.endswith("jsonl"):
        with open(predictions_path) as f:
            for line in f.readlines():
                predictions.append(json.loads(line))
    elif predictions_path.endswith("json"):
        predictions = json.load(open(predictions_path))
    else:
        raise ValueError("Predictions file must be in json or jsonl format")
    report_map = {}

    # Iterate through predictions
    report_map = {
        "no_generation": [],
        "generated": [],
        "with_logs": [],
        "install_fail": [],
        "reset_failed": [],
        "no_apply": [],
        "applied": [],
        "test_errored": [],
        "test_timeout": [],
        "resolved": [],
    }
    for p in tqdm(predictions, desc="Processing predictions", disable=not verbose):
        # Check if the model patch exists
        if p["model_patch"] == None or len(p["model_patch"].strip()) == 0:
            report_map["no_generation"].append(p[KEY_INSTANCE_ID])
            continue
        report_map["generated"].append(p[KEY_INSTANCE_ID])

        # Get log file
        log_path = os.path.join(log_dir, f"{p[KEY_INSTANCE_ID]}.{model}.eval.log")
        if not os.path.exists(log_path):
            continue
        report_map["with_logs"].append(p[KEY_INSTANCE_ID])
        log_content = open(log_path).read()

        # Check if there is an apply patch failure
        if any([
            f"{APPLY_PATCH_FAIL}; ({patch_type})" in log_content
            for patch_type in [
                PatchType.PATCH_PRED_TRY.value,
                PatchType.PATCH_PRED_MINIMAL_TRY.value
            ]
        ]):
            report_map["no_apply"].append(p[KEY_INSTANCE_ID])
            continue

        # Check if there is an installation failure
        if INSTALL_FAIL in log_content:
            report_map["install_fail"].append(p[KEY_INSTANCE_ID])
            continue

        # Check if there is a reset failure
        if RESET_FAILED in log_content:
            report_map["reset_failed"].append(p[KEY_INSTANCE_ID])
            continue

        # Get evaluation logs
        eval_sm, found = get_logs_eval(log_path)

        # Check if any tests errored or timed out
        for status in [
            ("test_errored", TESTS_ERROR),
            ("test_timeout", TESTS_TIMEOUT),
        ]:
            if status[1] in log_content:
                report_map[status[0]].append(p[KEY_INSTANCE_ID])
                continue

        # Check if patch failed to apply
        if not found:
            continue
        report_map["applied"].append(p[KEY_INSTANCE_ID])

        # Check if the patch was resolved
        report = get_eval_report(eval_sm, eval_refs[p[KEY_INSTANCE_ID]])
        if get_resolution_status(report) == ResolvedStatus.FULL.value:
            report_map["resolved"].append(p[KEY_INSTANCE_ID])

    return report_map
