

- Want a clean, simple, interpretable readout for one agent call to help us debug and understand details of why agent is failing
  - Still cool to log everything to a file. But ideally the terminal readout is 1 line per step amx
- Want good stats for multiple agent calls to get aggregate metrics to know what to prioritize


# Current Programmatic Patterns
python3 hackathon/evaluation/evaluate.py
python -m swebench.harness.run_evaluation \
    --predictions_path /path/to/all_preds.jsonl \
    --max_workers 1
    --run_id test


TODO:
[] Fix the issue where some questions fail bc they try to install a yanked package (types-pkg_resources). To replicate, simply run with question_index = 0
[] Add support for invoking the swebench evaluator after running the agent
[] Add support for meaningful parsing of the logs, using reference info from the question
  - Did we find the right file
  - Did we edit at least some of the right lines
  - Did our edit overlap with the gold edits in any way?

export PYTHONPATH="/Users/jp/Documents/GitHub/SWE-agent"


# Current Default Patterns

## Run
python run.py --model_name L3.1-70b \
  --instance_filter marshmallow-code__marshmallow-1359

python run.py --model_name gpt-4o-mini \
--per_instance_cost_limit .10 \
--config_file ./config/default.yaml

## Score
python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path /path/to/all_preds.jsonl \
    --max_workers 1
    --run_id test
    --split dev

For my machine
python -m swebench.harness.run_evaluation --dataset_name princeton-nlp/SWE-bench_Lite --predictions_path trajectories/jp/gpt-4o-mini__SWE-bench_Lite__default__t-0.00__p-0.95__c-0.05__install-1/all_preds.jsonl --max_workers 1 --run_id test --split dev