#!/usr/bin/env bash

set -euo pipefail

function stop_react {
    npx pm2 delete swe-agent
}

cd sweagent/frontend
npm install
trap stop_react exit
npx pm2 start --name swe-agent npm -- start

cd ../../
python sweagent/api/server.py
