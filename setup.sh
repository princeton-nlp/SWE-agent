#!/usr/bin/env bash

# bash strict mode
set -euo pipefail

echo "Setting up docker image for swe-agent..."
docker build -t sweagent/swe-agent:latest -f docker/swe.Dockerfile .

echo "Setting up docker image for evaluation..."
docker build -t sweagent/swe-eval:latest -f docker/eval.Dockerfile .

echo "Done with setup!"
