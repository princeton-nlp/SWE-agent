

- Want a clean, simple, interpretable readout for one agent call to help us debug and understand details of why agent is failing
  - Still cool to log everything to a file. But ideally the terminal readout is 1 line per step amx
- Want good stats for multiple agent calls to get aggregate metrics to know what to prioritize


# Current Default Patterns

## Run
python run.py --model_name L3.1-70b \
  --instance_filter marshmallow-code__marshmallow-1359

python run.py --model_name gpt-4o-mini \
--per_instance_cost_limit .10 \
--config_file ./config/default.yaml

## Score
python -m swebench.harness.run_evaluation \
    --predictions_path /path/to/all_preds.jsonl \
    --max_workers 1
    --run_id test

??
ValueError: Some prediction IDs not found in dataset!
Missing IDs:
marshmallow-code__marshmallow-1359