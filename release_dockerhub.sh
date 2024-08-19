#!/usr/bin/env bash

# This script builds the official docker images and pushes them to dockerhub
# after checking with the user.

# NOTE: To clear the buildx cache, run the following command:
# docker buildx prune --all or more specifically docker buildx rm <context_name>

# bash strict mode
set -euo pipefail

# Check if exactly one argument is supplied
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <user> <version>" >&2
    exit 1
fi

USER=${1}
VERSION_STR=${2}

if [[ -z "$USER" ]]; then
    echo "User name cannot be empty" >&2
    exit 3
fi
if [[ "$USER" != "sweagent" ]]; then
    echo "Careful here! Even if the username isn't sweagent, swe-eval will still be built on top of the sweagent/swe-agent image." >&2
    read -p "Do you want to proceed? (yes) " response
    if [[ "${response}" != "yes" ]]; then
        echo "Exiting..." >&2
        exit 4
    fi
fi


# The argument should be in the form of x.x.x where each x can be one or more digits
if [[ $VERSION_STR =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || [ "$VERSION_STR" = "latest" ]; then
    echo "Validated version number"
else
    echo "Argument must be 'latest' or in the form x.x.x, where x is one or more numbers." >&2
    exit 2
fi


DOCKER_CONTEXT_NAME="sweagent-multiplatform"
docker buildx use "$DOCKER_CONTEXT_NAME" ||  docker buildx create --use --name "$DOCKER_CONTEXT_NAME"

on_error() {
    echo "====> ERROR!!! IMPORTANT: Make sure that you've already pushed something to dockerhub or pushed the tag to github!" >&2
}
trap on_error ERR

echo "------------------------------------------"
echo "Building swe-agent"
echo "------------------------------------------"
docker buildx build  --platform=linux/amd64,linux/arm64  -t ${USER}/swe-agent:${VERSION_STR} -f docker/swe.Dockerfile --push .
echo "🔥 swe-agent pushed to dockerhub"
echo "------------------------------------------"
echo "Building swe-agent-run"
echo "------------------------------------------"
docker buildx build  --platform=linux/amd64,linux/arm64 -t ${USER}/swe-agent-run:${VERSION_STR} --push .
echo "🔥 swe-agent-run pushed to dockerhub"
echo "------------------------------------------"
echo "Building of all images done"
echo "------------------------------------------"
