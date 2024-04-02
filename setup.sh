#!/bin/bash

# Create docker image
echo "Setting up docker image for swe-agent..."
arch=$(uname -m)
if [[ "$arch" == "x86_64" ]]; then
  echo "Building the x86 Docker image"
  docker build -t swe-agent --build-arg MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-1-Linux-x86_64.sh -f docker/swe.Dockerfile .
elif [[ "$arch" == "aarch64" || "$arch" == "arm64" ]]; then
  echo "Ayy, arm64 in the house!"
  docker build -t swe-agent --build-arg MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py39_23.11.0-1-Linux-aarch64.sh -f docker/swe.Dockerfile .
else
  echo "unknown architecture detected?"
  echo $arch
  exit 1
fi

# build eval.Dockerfile
echo "Setting up docker image for evaluation..."
docker build -t swe-eval -f docker/eval.Dockerfile .

echo "Done with setup!"
