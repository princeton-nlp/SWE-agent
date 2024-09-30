set -euo pipefail

case $# in
  1)
    MANUAL_INPUT_ARGS=""
    ;;

  3)
    MANUAL_INPUT_ARGS="--manual_input_conversation_path $2 --manual_input_continuation_label $3"
    ;;

  *)
    echo "Usage: $0 <instance_id> [<manual_input_conversation_path> <manual_input_continuation_label>]"
    exit 1
    ;;
esac

set -x

echo $MANUAL_INPUT_ARGS

python3 run.py \
  --model_name "claude-sonnet-3.5" \
  --data_path "princeton-nlp/SWE-bench_Verified" \
  --config_file "./config/default_with_tools.yaml" \
  --per_instance_cost_limit 4.00 \
  --split "test" \
  --instance_filter "$1" \
  --skip_existing False \
  --cache_task_images \
  --tdd \
  $MANUAL_INPUT_ARGS

