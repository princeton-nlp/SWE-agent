#!/usr/bin/env bash

set -euo pipefail
set -x

sudo usermod -aG docker vscode
sudo chmod 666 /var/run/docker.sock
pip install -e '.'
