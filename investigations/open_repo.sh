#######################################################
# Open docker image for instance.
# Create it if it does not exist.
#######################################################

set -e
set -x

thisFile=$(readlink -f "$BASH_SOURCE")
thisDir=$(dirname "$thisFile")

instance_id=$1
if [[ -z $instance_id ]]; then
  echo "ERROR: \$1=instance_id missing."
  exit 1
fi

# Get ready...
image_id=$(python3 $thisDir/instance_data.py $instance_id)
container_name=$instance_id
# TODO: Get correct repo folder from instance_id.
repo_folder="/sympy__sympy"

# Get or create image and image_id from instance_id.
echo "Preparing Docker image..."
$thisDir/instance_image.sh $instance_id


# Check if the container is already running
existing_container=$(docker ps -q -f name=$instance_id)
echo "DDBG $existing_container"
if [ "$existing_container" ]; then
    echo "Container with name $instance_id is already running."
else
    # Check if the container exists but is not running
    if [ "$(docker ps -aq -f name=$instance_id)" ]; then
        echo "Container with name $instance_id exists but is not running. Starting the container..."
        docker start $instance_id
    else
        echo "Creating and starting a new container with name $instance_id."

        # Start the container and let it run indefinitely (in detached mode):
        docker run -d --name $container_name $image_id sleep infinity

        # Give it a sec.
        sleep 2

        # NOTE: We don't need to install anything.
        # # Install things.
        # $thisDir/setup_repo_image.sh $container_name
    fi
fi

# Check that its running:
docker ps

# NOTE: You can stop the container like this -
# docker stop $INSTANCE_ID

# TODO: Need to figure out in-developmen VSCode CLI features:
# see: https://github.com/microsoft/vscode-remote-release/issues/5278#issuecomment-1408712695
# code --remote container+$container_name:$repo_folder
code --folder-uri vscode-remote://attached-container+$(printf "$container_name" | xxd -p)$repo_folder
