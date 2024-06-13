#!/usr/bin/env bash

# bash strict mode
set -euo pipefail

export DOCKER_BUILDKIT=1

# TARGETARCH should be set automatically on most (but not all) systems, see
# https://github.com/princeton-nlp/SWE-agent/issues/245
echo "Setting up docker image for swe-agent..."
docker build -t gcr.io/reflectionai/swe-agent:local -f docker/swe.Dockerfile --build-arg TARGETARCH=$(uname -m) .

# echo "Setting up docker image for evaluation..."
docker build -t gcr.io/reflectionai/swe-eval:latest -f docker/eval.Dockerfile .
docker push gcr.io/reflectionai/swe-eval:latest

echo "Done with setup!"
