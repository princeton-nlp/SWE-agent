set -euo pipefail

# Stop all swe-agent containers.
img_name_partial="swe-agent-task-env-"
docker rm $(docker stop $(docker ps -a | grep "$yourImgName" | cut -d " " -f 1))
