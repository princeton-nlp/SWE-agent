#!/usr/bin/env bash

set -euo pipefail
set -x

# Run from repo root

sudo usermod -aG docker vscode
sudo chmod 666 /var/run/docker.sock
pip install -e '.'
cp .devcontainer/sample_keys.cfg keys.cfg
cat .devcontainer/bashrc_epilog.sh >> ~/.bashrc

# Install nodejs
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - &&\
sudo apt-get install -y nodejs
