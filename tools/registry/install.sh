#!/usr/bin/env bash

# script_dir=$(dirname "$(readlink -f "$0")")
bundle_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# source "$script_dir/lib/utils.sh"

export PYTHONPATH=$PYTHONPATH:"$bundle_dir/lib"