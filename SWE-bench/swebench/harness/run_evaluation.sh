#!/bin/bash
python run_evaluation.py \
    --predictions_path "<path to predictions (.json)>" \
    --swe_bench_tasks "<path to `swe-bench.json`>" \
    --log_dir "<path to folder>" \
    --testbed "<path to folder>" \
    --skip_existing \
    --timeout 900 \
    --verbose
