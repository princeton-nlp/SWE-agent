#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [ -f "$SCRIPT_DIR/lib/utils.sh" ]; then
    source "$SCRIPT_DIR/lib/utils.sh"
fi

if [ -z "$WINDOW" ]; then
    echo "Error: WINDOW not set"
    exit 1
fi
if [ -z "$OVERLAP" ]; then
    echo "Error: OVERLAP not set"
    exit 1
fi

_write_env "WINDOW" "${WINDOW:-100}"
_write_env "OVERLAP" "${OVERLAP:-2}"
_write_env "CURRENT_LINE" "${CURRENT_LINE:-0}"
_write_env "CURRENT_FILE" "${CURRENT_FILE:-}"

# install jq
apt-get update && apt-get install -y jq
