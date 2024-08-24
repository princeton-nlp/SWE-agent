#!/usr/bin/env zsh

for f in ~/LLM_CTF_Dataset_Dev/**/challenge.json
do
    python run.py \
        --image_name sweagent/swe-ctf:latest --model_name gpt-4o-mini \
        --data_path "$f"  \
        --repo_path "$(dirname $f)" \
        --config_file config/default_ctf_retry_5_gtc_hints_mini.yaml \
        --per_instance_cost_limit 0.05 --noprint_config
done
