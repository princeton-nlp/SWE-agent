#!/usr/bin/env bash

# This script builds the official docker images and pushes them to dockerhub
# after checking with the user.

# bash strict mode
set -euo pipefail

# Check if exactly one argument is supplied
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <version>" >&2
    exit 1
fi

VERSION_STR=${1}


# The argument should be in the form of x.x.x where each x can be one or more digits
if [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Validated version number"
else
    echo "Argument must be in the form x.x.x, where x is one or more numbers." >&2
    exit 2
fi


echo "------------------------------------------"
echo "Building swe-agent"
echo "------------------------------------------"
docker build -t sweagent/swe-agent:${VERSION_STR} --build-arg MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-1-Linux-aarch64.sh -f docker/swe.Dockerfile .
docker build -t sweagent/swe-agent:latest --build-arg MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-1-Linux-aarch64.sh -f docker/swe.Dockerfile .
echo "------------------------------------------"
echo "Building swe-eval"
echo "------------------------------------------"
docker build -t sweagent/swe-eval:${VERSION_STR} -f docker/eval.Dockerfile .
docker build -t sweagent/swe-eval:latest -f docker/eval.Dockerfile .
echo "------------------------------------------"
echo "Building swe-agent-run"
echo "------------------------------------------"
docker build -t sweagent/swe-agent-run:${VERSION_STR} .
docker build -t sweagent/swe-agent-run:latest .
echo "------------------------------------------"
echo "Building of all images done"
echo "------------------------------------------"
read -p "Do you want to push to dockerhub and add the tag to github? (yes to proceed) " answer

if [ "$answer" != "yes" ]; then
    echo "Abort; Bye" >&2
    exit 3
fi

# Check if the tags already exist on Docker Hub
IMAGES=("sweagent/swe-agent:${VERSION_STR}" "sweagent/swe-agent:latest" "sweagent/swe-eval:${VERSION_STR}" "sweagent/swe-eval:latest" "sweagent/swe-agent-run:${VERSION_STR}" "sweagent/swe-agent-run:latest")
for image in "${IMAGES[@]}"; do
    if [[ $image == *"latest"* ]]; then
        continue
    fi
    IMAGE_NAME="${image%:*}"
    TAG="${image##*:}"
    URL="https://hub.docker.com/v2/repositories/${IMAGE_NAME}/tags/${TAG}/"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${URL}")
    if [ "$HTTP_STATUS" -eq 200 ]; then
        echo "The tag '${TAG}' exists for '${IMAGE_NAME}' on Docker Hub." >&2
        echo "Abort" >&2
        exit 4
    fi
done

docker login || {
    echo "Failed to login to dockerhub" >&2
    exit 8
}

# Let's get serious
# Function to execute upon exit
on_error() {
    echo "====> ERROR!!! IMPORTANT: Make sure if you've already pushed something to dockerhub or pushed the tag to github!" >&2
}
trap on_error ERR

git tag v${VERSION_STR} || {
    echo "Failed to create a tag in git" >&2
    exit 5
}
echo "🔥 Tag v${VERSION_STR} created in git!"

git push origin v${VERSION_STR} || {
    echo "Failed to push the tag to github" >&2
    exit 6
}
echo "🔥 Tag v${VERSION_STR} pushed to github"

for image in "${IMAGES[@]}"; do
    docker push ${image}
    echo "🔥 Pushed ${image} to dockerhub"
done
