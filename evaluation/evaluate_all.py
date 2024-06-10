import argparse
import ast
import pathlib
import evaluation
import schema
import pandas as pd
import rich
from rich import console
import uuid

import tqdm

_LOG_DIR = pathlib.Path("/log_dir/")
_TESTBED = pathlib.Path("/testbed/")
_PREDICTIONS_PATH = pathlib.Path("/predictions.jsonl")
_SWE_BENCH_PATH = pathlib.Path("/swe_bench_tasks.jsonl")
_CONSOLE = console.Console()


def _fix_list_column(x: 'str | list[str]'):
    return ast.literal_eval(x) if isinstance(x, str) else x


def main(dataset_path: pathlib.Path):
    unique_filename = f"no_op_{uuid.uuid4()}.txt"

    # Create a patch that adds a new file with a blank line
    no_op_patch = f"""
diff --git a/{unique_filename} b/{unique_filename}
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/{unique_filename}
@@ -0,0 +1 @@
+
"""
    _LOG_DIR.mkdir(exist_ok=True)
    _TESTBED.mkdir(exist_ok=True)
    df = pd.read_parquet(dataset_path)
    for column in ["PASS_TO_PASS", "FAIL_TO_PASS"]:
        df[column] = df[column].apply(_fix_list_column)
    df.to_json(_SWE_BENCH_PATH, orient='records', lines=True)

    succeeding_gold_patches = 0
    failing_null_patches = 0

    for i, row in tqdm.tqdm(df.iterrows(), total=len(df)):
        assert isinstance(row, pd.Series)
        data_point = schema.DataPoint.model_validate(row.to_dict())

        def run_evaluation(patch: str):
            all_preds = schema.AllPreds(model_name_or_path='none',
                                        instance_id=data_point.instance_id,
                                        model_patch=patch)
            _PREDICTIONS_PATH.unlink(missing_ok=True)
            _PREDICTIONS_PATH.write_text(all_preds.model_dump_json())
            return schema.Report.model_validate(
                evaluation.main(
                    predictions_path=str(_PREDICTIONS_PATH),
                    log_dir=str(_LOG_DIR),
                    testbed=str(_TESTBED),
                    skip_existing=False,
                    swe_bench_tasks=str(_SWE_BENCH_PATH),
                    timeout=900,
                    verbose=False,
                    conda_link=None,
                    log_suffix=None,
                    num_processes=-1,
                ))

        print()
        _CONSOLE.rule(f"[bold]Evaluating {data_point.instance_id}[/bold]")

        null_patch_report = run_evaluation(patch=no_op_patch)
        if not null_patch_report.resolved:
            _CONSOLE.print(
                f"[bold]👍 Null patch did not resolve instance.[/bold]")
            failing_null_patches += 1

        gold_patch_report = run_evaluation(patch=data_point.patch)
        if gold_patch_report.resolved:
            _CONSOLE.print(f"[bold]👍 Gold patch did resolve instance.[/bold]")
            succeeding_gold_patches += 1
        _CONSOLE.print(
            f"[bold]{failing_null_patches}/{i+1} null patches failed[/bold]")
        _CONSOLE.print(
            f"[bold]{succeeding_gold_patches}/{i+1} gold patches succeeded[/bold]"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset_path",
        type=str,
        help="Path to directory containing predictions files (.jsonl)",
        required=True,
    )
    args = parser.parse_args()
    main(dataset_path=pathlib.Path(args.dataset_path), )
