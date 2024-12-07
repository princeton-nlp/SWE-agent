#!/bin/bash

export ANTHROPIC_API_KEY=XXX
repos=(
    "simpy"
    "wcwidth"
    "parsel"
    "chardet"
    "minitorch"
    "tinydb"
    "deprecated"
    "voluptuous"
    "cachetools"
    "imapclient"
    "marshmallow"
    "jinja"
    "cookiecutter"
    "portalocker"
    "pyjwt"
    "babel"
    "statsmodels"
    "python-progressbar"
    "xarray"
    "imbalanced-learn"
    "web3.py"
    "scrapy"
    "seaborn"
    "pypdf"
    "pexpect"
    "pytest"
    "pylint"
    "joblib"
    "dulwich"
    "virtualenv"
    "networkx"
    "requests"
    "sphinx"
    "jedi"
    "moviepy"
    "loguru" #####
    "paramiko"
    "geopandas"
    "bitstring"
    "fastapi"
    "tornado"
    "python-prompt-toolkit"
    "attrs"
    "PyBoy"
    "pydantic"
    "filesystem_spec"
    "tlslite-ng"
    "graphene"
    "mimesis"
    "dnspython"
    "python-rsa"
    "more-itertools"
    "click"
    "fabric"
    "flask"
    "sqlparse"
)

for repo in "${repos[@]}"; do
    echo "Processing $repo..."

    python run.py \
        --model_name claude-3-5-sonnet-20240620 \
        --data_path "commit0_prepare/repos/$repo/my_issue_$repo.md" \
        --repo_path "commit0_prepare/empty_repo" \
        --config_file "config/commit0/prompt/$repo.yaml" \
        --image_name wentingzhao/$repo:v0 \
        --per_instance_cost_limit 1.00 \
        --apply_patch_locally > "log/commit0/$repo.log" 2>&1

    echo "Completed $repo"
done

echo "All repos processed"