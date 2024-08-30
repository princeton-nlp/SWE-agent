#######################################################
# Get or create docker image for instance.
#######################################################

set -e

if [ -z "$BASH_SOURCE" ]; then
  # NOTE: When running the script through Python's subprocess, BASH_SOURCE does not exist.
  thisFile="$0"
  if [ -z "$0" ]; then
    echo "ERROR: Could not deduce path of script"
    exit 1
  fi
else
  thisFile=$(readlink -f "$BASH_SOURCE")
fi
thisDir=$(dirname "$thisFile")

instance_id=$1
if [[ -z $instance_id ]]; then
  echo "ERROR: \$1=instance_id missing."
  exit 1
fi
# Get image_id from instance_id.
image_id=$(python3 $thisDir/instance_data.py $instance_id)

# Check if image exists.
image_exists=$(docker images -q $image_id)

if [[ -z $image_exists ]]; then
  # Create image.
  cd $thisDir/..
  python3 run.py \
    --model_name "claude-sonnet-3.5" \
    --data_path="princeton-nlp/SWE-bench_Verified" \
    --split "test" \
    --instance_filter "$instance_id" \
    --cache_task_images \
    --init_only
  
  # Install extra dependencies.
  $thisDir/setup_repo_image.sh $image_id
fi

