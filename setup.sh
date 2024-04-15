#!/usr/bin/env bash

# bash strict mode
set -euo pipefail

# Detect the architecture of the host system and export it
export ARCH=$(uname -m)

echo "Setting up docker image for swe-agent..."
docker build --build-arg TARGETARCH="$ARCH" -t sweagent/swe-agent:latest -f docker/swe.Dockerfile .

echo "Setting up docker image for evaluation..."
docker build --build-arg TARGETARCH="$ARCH" -t sweagent/swe-eval:latest -f docker/eval.Dockerfile ../

echo "Done with setup!"
