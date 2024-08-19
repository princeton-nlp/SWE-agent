#!/usr/bin/env bash

# bash strict mode
set -euo pipefail

echo "Setting up docker image for swe-agent..."
# TARGETARCH should be set automatically on most (but not all) systems, see
# https://github.com/princeton-nlp/SWE-agent/issues/245
docker build -t sweagent/swe-agent:latest -f docker/swe.Dockerfile --build-arg TARGETARCH=$(uname -m) .

echo "Done with setup!"
