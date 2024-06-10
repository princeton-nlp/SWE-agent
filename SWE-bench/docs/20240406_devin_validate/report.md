# Validating Devin's Results
April 6, 2024

In this report, we briefly detail our validation of [Devin](https://www.cognition-labs.com/introducing-devin), an AI software engineer released by [Cognition Labs](https://www.cognition-labs.com/) that resolves an impressive 13.86% of issues on a random 25% subset of SWE-bench.

The Cognition Labs team released their own [report on Devin's performance on SWE-bench](https://www.cognition-labs.com/post/swe-bench-technical-report), which includes a much more thorough deep dive into where Devin excels and struggles.

Our report focuses solely on validating Devin's performance. To this end, we do the following:
1. Compile the open-sourced Devin predictions ([Github repository](https://github.com/CognitionAI/devin-swebench-results/tree/main)) into a SWE-bench evaluation-compatible `.jsonl` file.
2. Run evaluation on these predictions with:
```shell
python evaluation.py \
    --predictions_path devin_all_preds.jsonl \
    --swe_bench_tasks swe-bench.json \
    --log_dir ./results/ \
    --testbed ./testbed/ \
    --skip_existing \
    --timeout 1200 \
    --verbose
```

[To Do: Results]

✍️ Carlos & John