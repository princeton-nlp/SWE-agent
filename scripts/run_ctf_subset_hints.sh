#!/usr/bin/env zsh

while IFS= read -r f
do
    f="$HOME/LLM_CTF_Dataset_Dev/$f"
    echo $f;
    python run.py \
        --image_name sweagent/swe-ctf:latest --model_name azure:gpt4o \
        --data_path "$f"  \
        --repo_path "$(dirname $f)" \
        --config_file config/default_ctf_retry_5_gtc_hints.yaml \
        --per_instance_cost_limit 1.5 --noprint_config
done < ~/ctf_dev_subset.txt
