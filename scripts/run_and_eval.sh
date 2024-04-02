#!/bin/bash
#this script runs and evaluates the agent N times.
#to run:
#bash run_and_eval.sh '' default_with_inclusive_edit_demo_v2 data/dev-easy/swe-bench-dev-easy-med.json 3
# vars:                suffix   template                        data                                    number of runs

# define user variables
suffix=${1:-''}
template=$2
dataset_path=$3
num_runs=$4

# extract filename from the dataset path
dataset_name=`basename $dataset_path`

for((i=1; i<=num_runs; i++)); do
	# command 1
	python run.py --model_name gpt4 --data_path $dataset_path --config_file config/configs/$template.yaml --suffix ${suffix}run${i} --temperature 0.2 --top_p 0.95 --per_instance_cost_limit 3.00 --install_environment 1

	# command 2
	python evaluation/evaluation.py \
		--predictions_path trajectories/$USER/gpt4__${dataset_name}__$template__t-0.20__p-0.95__c-3.00__install-1__${suffix}run${i}/all_preds.jsonl \
		--swe_bench_tasks $dataset_path \
		--log_dir ./results \
		--testbed ./testbed \
		--skip_existing \
		--timeout 900 \
		--verbose
done
