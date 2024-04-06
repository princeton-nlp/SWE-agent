#!/usr/bin/env bash

# bash strict mode
set -euo pipefail

# Check if exactly one argument is supplied
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <docker-username> <version>" >&2
    exit 1
fi

DOCKER_USERNAME=${1}
VERSION_STR=${2}

# Ensure jq is installed
if ! command -v jq &> /dev/null; then
    echo "jq could not be found, please install jq to continue."
    exit 1
fi


# Validate version format
if [[ $VERSION_STR =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Validated version number"
else
    echo "Argument must be in the form x.x.x, where x is one or more numbers." >&2
    exit 2
fi

if [ -z "${DOCKER_USERNAME}" ]; then
    echo "Docker username is required" >&2
    exit 3
fi

# Determine architecture
ARCH=$(uname -m)
case "$ARCH" in
    aarch64) ARCH_SUFFIX="arm64" ;;
    arm64) ARCH_SUFFIX="arm64" ;;
    x86_64) ARCH_SUFFIX="amd64" ;;
    *) echo "Unsupported architecture" >&2; exit 7 ;;
esac

# Set the Miniconda URL based on architecture
if [ "$ARCH_SUFFIX" == "arm64" ]; then
    MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-1-Linux-aarch64.sh
else
    MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-1-Linux-x86_64.sh
fi

echo "------------------------------------------"
echo "Building images for $ARCH_SUFFIX - ${VERSION_STR}"
echo "------------------------------------------"

# Build and push version-specific tag
docker build -t ${DOCKER_USERNAME}/swe-agent:${VERSION_STR}-${ARCH_SUFFIX} --build-arg MINICONDA_URL=${MINICONDA_URL} -f docker/swe.Dockerfile .
docker push ${DOCKER_USERNAME}/swe-agent:${VERSION_STR}-${ARCH_SUFFIX}

# Build and push latest tag
docker build -t ${DOCKER_USERNAME}/swe-agent:latest-${ARCH_SUFFIX} --build-arg MINICONDA_URL=${MINICONDA_URL} -f docker/swe.Dockerfile .
docker push ${DOCKER_USERNAME}/swe-agent:latest-${ARCH_SUFFIX}

# Repeat the build and push process for other Dockerfiles as necessary

echo "------------------------------------------"
echo "Building of all images for $ARCH_SUFFIX - ${VERSION_STR} complete"
echo "------------------------------------------"

read -p "Do you want to proceed with manifest creation for version and latest tags? (yes/no) " answer
if [ "$answer" != "yes" ]; then
    echo "Skipping manifest creation. Process complete."
    exit 0
fi


# Function to check if a specific tag exists for an image on Docker Hub
check_image_tag_exists() {
    local username=$1
    local image=$2
    local tag=$3
    local token=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${username}/${image}:pull" | jq -r .token)
    local tag_exists=$(curl -s -H "Authorization: Bearer ${token}" "https://registry-1.docker.io/v2/${username}/${image}/tags/list" | jq -r ".tags | .[] | select(. == \"${tag}\")")

    if [[ -z "$tag_exists" ]]; then
        echo "ERROR: The image ${username}/${image}:${tag} does not exist on Docker Hub." >&2
        echo "Please push the image before creating the manifest." >&2
        exit 9
    else
        echo "The image ${username}/${image}:${tag} exists on Docker Hub."
    fi
}

for ARCH in "amd64" "arm64"; do
    check_image_tag_exists ${DOCKER_USERNAME} "swe-agent" "${VERSION_STR}-${ARCH}"
    check_image_tag_exists ${DOCKER_USERNAME} "swe-agent" "latest-${ARCH}"
done

# Create and push the manifest for the version tag
export DOCKER_CLI_EXPERIMENTAL=enabled
docker manifest create -a ${DOCKER_USERNAME}/swe-agent:${VERSION_STR} \
  ${DOCKER_USERNAME}/swe-agent:${VERSION_STR}-amd64 \
  ${DOCKER_USERNAME}/swe-agent:${VERSION_STR}-arm64

docker manifest annotate ${DOCKER_USERNAME}/swe-agent:${VERSION_STR} ${DOCKER_USERNAME}/swe-agent:${VERSION_STR}-arm64 --os linux --arch arm64
docker manifest annotate ${DOCKER_USERNAME}/swe-agent:${VERSION_STR} ${DOCKER_USERNAME}/swe-agent:${VERSION_STR}-amd64 --os linux --arch amd64

docker manifest push ${DOCKER_USERNAME}/swe-agent:${VERSION_STR}

# Create and push the manifest for the latest tag
docker manifest create -a ${DOCKER_USERNAME}/swe-agent:latest \
  ${DOCKER_USERNAME}/swe-agent:latest-amd64 \
  ${DOCKER_USERNAME}/swe-agent:latest-arm64

docker manifest annotate ${DOCKER_USERNAME}/swe-agent:latest ${DOCKER_USERNAME}/swe-agent:latest-arm64 --os linux --arch arm64
docker manifest annotate ${DOCKER_USERNAME}/swe-agent:latest ${DOCKER_USERNAME}/swe-agent:latest-amd64 --os linux --arch amd64

docker manifest push ${DOCKER_USERNAME}/swe-agent:latest

echo "Manifests for version ${VERSION_STR} and latest created and pushed."

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

read -p "Do you want to proceed with git tag (v${VERSION_STR}) creation and pushing to github? (yes/no) " answer
if [ "$answer" != "yes" ]; then
    echo "Skipping git tag creation and pushing to github. Process complete."
    exit 0
fi

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
