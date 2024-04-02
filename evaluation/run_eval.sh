#!/bin/bash

# The first positional argument
predictions_path=$1

# Check if predictions_path is not provided
if [ -z "$predictions_path" ]; then
    echo "Usage: $0 <predictions_path> [dataset_name_or_path] [results_dir] [testbed_dir]"
    exit 1
fi

# Default values for the optional arguments
dataset_name_or_path="${2:-princeton-nlp/SWE-bench}"
results_dir="${3:-results}"
testbed_dir="${4:-testbed}"

# If results or testbed directories do not exist, create them
if [ ! -d "$results_dir" ]; then
    mkdir -p "$results_dir"
    echo "Created results directory at $results_dir"
fi

if [ ! -d "$testbed_dir" ]; then
    mkdir -p "$testbed_dir"
    echo "Created testbed directory at $testbed_dir"
fi

# Run the Python script with the specified arguments
python evaluation.py \
    --predictions_path "$predictions_path" \
    --swe_bench_tasks "$dataset_name_or_path" \
    --log_dir "$results_dir" \
    --testbed "$testbed_dir" \
    --skip_existing \
    --timeout 900 \
    --verbose
