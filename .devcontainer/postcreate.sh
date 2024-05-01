#!/usr/bin/env bash

set -euo pipefail
set -x

pip install -e '.'
docker pull sweagent/swe-agent
