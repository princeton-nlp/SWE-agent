# Benchmarking

!!! note "Scope"
    This page talks about benchmarking on SWE-bench to measure the software engineering capabilities of SWE-agent.
    Benchmarking for the other modes (programming challenges, cybersecurity) are coming soon.

There are two steps to the SWE-agent/SWE-bench pipeline. First SWE-agent takes an input GitHub issue and returns a pull request that attempts to fix it. We call that step *inference*. The second step (currently only available for issues in the SWE-bench benchmark) is to *evaluate* the pull request to verify that it has indeed fixed the issue.

!!! warning "Architectures"
    At this moment, there are known issues with a small number of repositories that don't install properly for `arm64` / `aarch64` architecture computers. We're working on a fix, but if you'd like to run and evaluate on the entirety of SWE-bench, the easiest way is by using an `x86` machine.

## 👩‍💻 Inference <a name="inference"></a>

Run SWE-agent on [SWE-bench Lite](https://www.swebench.com/lite.html) and generate patches.

```bash
python run.py --model_name gpt4 \
  --per_instance_cost_limit 2.00 \
  --config_file ./config/default.yaml
```

If you'd like to run on a *single* issue from SWE-bench, use the `--instance_filter` option as follows:
```bash
python run.py --model_name gpt4 \
  --instance_filter marshmallow-code__marshmallow-1359
```

The above examples use the default value of `--data_path` (`princeton-nlp/SWE-bench_Lite`, which will be looked up from huggingface).
You can specify any other huggingface datasets as well, or supply the path to a pre-downloaded dataset.
By default, SWE-agent evaluates on the `dev` split of that dataset.
You can change that by supplying the `--split` argument to the above commands (obviously you shouldn't tune your model on the `test` dataset).

## 🧪 Evaluation <a name="evaluation"></a>

!!! note "Previous `evaluation/` scripts"

    We have removed the scripts that were previously in the `evaluation/` subfolder.
    They were relatively thin wrappers around `swe-bench`. After the `swe-bench` 2.0 update, we recommend to use `swe-bench` directly.

You can directly run SWE-bench to evaluate the SWE-agent results.

After installing SWE-bench, you can run `run_evaluation` as such:

```bash
python -m swebench.harness.run_evaluation \
    --predictions_path /path/to/all_preds.jsonl \
    --max_workers 1 \
    --run_id test \
    --split dev
```

Head over to [SWE-bench](https://github.com/princeton-nlp/SWE-bench/) for details.

!!! note "Default split"

    When running `swe-agent` it uses the SWE-bench lite `dev` split by default (i.e., when not specifying `--data_path` or `--split`).
    However, `swe-bench` assumes the SWE-bench lite `test` split by default.
    When you get warnings from `swe-bench` about missing instances, make sure you specify `--split test` or `--split dev` appropriately.

{% include-markdown "../_footer.md" %}
