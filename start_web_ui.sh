#!/usr/bin/env bash

set -euo pipefail

this_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

function stop_react {
    npx --prefix "${this_dir}/sweagent/frontend" pm2 delete swe-agent
}

cd sweagent/frontend
npm install
trap stop_react exit
npx pm2 start --name swe-agent npm -- start

cd ../../
python sweagent/api/server.py
