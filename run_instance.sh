set -e
set -x

# This runs the instance from the official SWE-agent demo video.
# See: https://www.youtube.com/watch?v=CeMtJ4XObAM
python3 run.py \
  --model_name "claude-sonnet-3.5" \
  --data_path "princeton-nlp/SWE-bench_Verified" \
  --config_file "./config/default_with_tools.yaml" \
  --per_instance_cost_limit 4.00 \
  --split "test" \
  --instance_filter "$1" \
  --skip_existing False \
  --cache_task_images

