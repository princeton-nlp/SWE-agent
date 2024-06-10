# Evaluating with SWE-bench
John Yang &bull; November 6, 2023

In this tutorial, we will explain how to evaluate models and methods using SWE-bench.

## 🤖 Creating Predictions
For each task instance of the SWE-bench dataset, given an issue (`problem_statement`) + codebase (`repo` + `base_commit`), your model should attempt to write a diff patch prediction. For full details on the SWE-bench task, please refer to Section 2 of the main paper.

Each prediction must be formatted as follows:
```json
{
    "instance_id": "<Unique task instance ID>",
    "model_patch": "<.patch file content string>",
    "model_name_or_path": "<Model name here (i.e. SWE-Llama-13b)>",
}
```

Store multiple predictions in a `.json` file formatted as `[<prediction 1>, <prediction 2>,... <prediction n>]`. It is not necessary to generate predictions for every task instance.

If you're more interested in specifically running evaluation to see how it works, you can download and use this set of [predictions](https://drive.google.com/uc?export=download&id=11a8mtuX6cafsdVDJAo-Bjw8X7zHS8EYx) that is an example of what your predictions should look like.

## 🔄 Running Evaluation
To run evalution, modify then run the `harness/run_evaluation.sh` script, which invokes the `run_evaluation.py` script. The following arguments are necessary:

```bash
python run_evaluation.py \
    --predictions_path <Path to predictions .json file> \
    --swe_bench_tasks <Path to `swe-bench.json` file> \
    --log_dir <Path to folder to write per-task instance logs to> \
    --testbed <Path to temporary directory to execute each task instance>
```

Additional arguments are defined in `run_evaluation.py`. The following diagram captures, at a high level, what `run_evaluation.py` does. More details are provided in `harness/` and the Appendix of the main paper.

<div align="center">
    <img style="width:70%" src="../assets/evaluation.png">
</div>

## 📈 Metrics

Upon the successful completion of `./run_evaluation.sh`, a log file should have been created for each prediction and stored within `log_dir`, where the log file is named with the following format: `<instance_id>.<model>.eval.log`.


To get the evaluation results of a model, use the `get_model_report` function within `metrics/report.py`. It takes the same set of parameters as `harness/run_evaluation.sh`

Here is a code snippet demonstrating its proper usage:

```python
model = "Model name (same as moniker used for predictions)"
predictions_path = "Path to predictions .json file"
swe_bench_tasks = "Path to `swe-bench.json` file"
log_dir = "Path to folder with per-task instance logs (same as `log_dir` from above)"

report = get_model_report(model, predictions_path, swe_bench_tasks, log_dir)

for k, v in report.items():
    print(f"- {k}: {len(v)}")
```

Given the model name, the `get_model_report` function returns a dictionary formatted as follows:
```json
{
    "no_generation": ["instance_ids"],
    "generated": ["instance_ids"],
    "with_logs": ["instance_ids"],
    "install_fail": ["instance_ids"],
    "reset_failed": ["instance_ids"],
    "no_apply": ["instance_ids"],
    "applied": ["instance_ids"],
    "test_errored": ["instance_ids"],
    "test_timeout": ["instance_ids"],
    "resolved": ["instance_ids"],
}
```

Each key-value entry is a pairing of a repository with the outcome of each prediction, identified by `instance_id`:
* `no_generation`: The prediction was `None`.
* `generated`: The prediction was non-empty.
* `with_logs`: A log file was created for this prediction (should `=` no. of `generated`).
* `install_fail`: The execution environment failed to install properly.
* `reset_failed`: The GitHub repository of the execution environment could not be checked out properly.
* `no_apply`: The prediction was not applied as a patch successfully.
* `applied`: The prediction was applied as a patch successfully.
* `test_errored`: The test command errored out.
* `test_timeout`: The test command timed out.
* `resolved`: The prediction passed all tests.

Some notes on understanding the report numbers:
* `no_generation` + `generated` = Total number of predictions.
* `generated` >= `applied` >= `resolved`.
* % Resolved Rate =
    * `resolved` / 300 for SWE-bench lite
    * `resolved` / 2294 for SWE-bench test
    * `resolved` / (`no_generation` + `generated`) generally
