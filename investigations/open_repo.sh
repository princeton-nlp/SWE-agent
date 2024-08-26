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

# Get or create image and image_id from instance_id.
echo "Preparing Docker image..."
image_id=$($thisDir/instance_image.sh $instance_id)
container_name=$instance_id
repo_folder="/sympy__sympy"

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

        # Start the container and let it run indefinitely:
        docker run -d --name $container_name $image_id sleep infinity
        sleep 2

        # Install things.
        $thisDir/setup_repo_image.sh $container_name
        
        # Start code-server.
        # TODO: "sudo: systemctl: command not found"
        # TODO: Instead, check what the VSCode's Attach command does when it asks to auto-install code-server!
        docker exec $container_name /bin/sh -c "sudo systemctl enable --now code-server@\$USER"
    fi
fi

# Give it a sec.
sleep 1

# Check that its running:
docker ps

# NOTE: You can stop the container like this -
# docker stop $INSTANCE_ID

# TODO: This won't work. Always errors with:
#           "Failed to connect to the remote extension host server (Error: No remote extension installed to resolve container.)"
code --remote container+$container_name:$repo_folder
