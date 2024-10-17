#!/usr/bin/env bash

# bash strict mode
set -euo pipefail

docker build -t sweagent/swe-agent:latest -f SWE-agent/docker/update_swe_rex.Dockerfile --build-arg TARGETARCH=$(uname -m) .

echo "Done with setup!"
