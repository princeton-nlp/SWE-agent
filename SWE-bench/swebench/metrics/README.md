# Metrics
This folder defines utilities for parsing validation/evaluation logs, calculating evaluation metrics (i.e. % resolved), and retrieving result and evaluation-oriented data structures quickly.
We present an overview of the available tools.

**`getters.py`**

A number of getter functions for converting raw logs and evaluation data structures into results. The available functions are the following:

* `get_diffs(sm_1: Dict, sm_2: Dict)`: Compare two evaluation `status_map`s to get which tests have different results.
* `get_logs_eval(log_fp: str)`: Given an evaluation log file, this function returns an evaluation `status_map`.
* `get_logs_gold(log_fp: str)`: Given a validation log file, this function returns logs of the test results from before and after the gold patch is applied.
* `log_path_to_sms(log_fp: str, log_parser)`: Given a validation log file, this function returns `status_map`s of the test results from before and after the gold patch is applied.

<hr />

**`log_parsers.py`**

Contains repository-specific functions that define how to parse evaluation and validation logs for test results.
All functions are named with the `parse_log_*` header, where each function takes in a log and returns an evaluation `status_map`.
This file is used extensively by the rest of the functionalities in `metrics/`.

<hr />

**`conversion.py`**

Parses validation logs into an evaluation data structure which is referred to in the code as a `status_map`.
```
{'FAIL_TO_FAIL': ['test'], 'FAIL_TO_PASS': ['test'], 'PASS_TO_FAIL': ['test'], 'PASS_TO_PASS': ['test']}
```

This script is used to create the `swe-bench-eval-refs.json` data that is the test results for the gold patch.

<hr />

**`report.py`**

This file contains the main logic for comparing evaluation log test results against gold patch `status_map` data structures
to determine whether a prediction resolved an issue.
Given a prediction's `status_map` and a gold patch `status_map`, `get_eval_report` returns the following data structure:
```
{
    'FAIL_TO_FAIL': {'success': ['tests'], 'failures': ['tests']},
    'FAIL_TO_PASS': {'success': ['tests'], 'failures': ['tests']},
    'PASS_TO_FAIL': {'success': ['tests'], 'failures': ['tests']},
    'PASS_TO_PASS': {'success': ['tests'], 'failures': ['tests']},
}
```
Where `success` and `failure` point to list of tests. `success` refers to tests where the results of the prediction 
`status_map` matches that of the gold patch, and `failure` refers to otherwise.

For instance, given an evaluation `status_map` that looks like the following:
```
{
    'test_a': FAIL, 'test_b': FAIL, 'test_c': PASS, 'test_d': PASS
}
```
And a gold patch `status_map` like the following:
```
{
    'FAIL_TO_PASS': ['test_a', 'test_c'],
    'PASS_TO_PASS': ['test_b', 'test_d']
}
```
Then the report would look like the following:
```
{
    'FAIL_TO_PASS': {
        'success': ['test_c'],
        'failure': ['test_a'],
    },
    'PASS_TO_PASS': {
        'success': ['test_d'],
        'failure': ['test_b'],
    }
}
```
The file also defines additional wrapper functions around `get_eval_report` to generations reports for lists or directories of predictions reports.

<hr />

**`metrics.py`**

This file contains functions for computing a number of evaluation metrics, including...
* `get_resolution_status(report: Dict)`: Given a prediction's `report`, returns a value indicating whether the issue was fully resolved, partially resolved, or not resolved.
* `compute_pass_to_pass(report: Dict)`: Given a prediction's `report`, returns the `fail_to_pass` rate for the prediction.
* `compute_fail_to_pass(report: Dict)`: Given a prediction's `report`, returns the `pass_to_pass` rate for the prediction.

Functions for calculation the [un]weighted f2p and p2p scores across multiple prediction `report`.

<hr />

**`monitor.py`**

This file contains functions that string together multiple functions from above to gather evaluation statistics automatically
from a directory of evaluation or validation logs.
* `monitor_validation(path_to_logs: str, log_prefix: str)`: Point this function at a directory of validation logs to get statistics on which task instances were executed successfully.
* `monitor_logs_same_diff(log_dir: str, repo: str = None)`: Point this function at a directory of validation logs to check which task instances have pre-gold patch and post-gold patch logs that are different.