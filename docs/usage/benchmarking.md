# Benchmarking

There are two steps to the SWE-agent pipeline. First SWE-agent takes an input GitHub issue and returns a pull request that attempts to fix it. We call that step *inference*. The second step (currently, only available for issues in the SWE-bench benchmark) is to *evaluate* the pull request to verify that it has indeed fixed the issue. 

!!! warning "Architectures"
    At this moment, there are known issues with a small number of repositories that don't install properly for `arm64` / `aarch64` architecture computers. We're working on a fix, but if you'd like to run and evaluate on the entirety of SWE-bench, the easiest way is by using an `x86` machine.

## 👩‍💻 Inference <a name="inference"></a>
**Inference on *any* GitHub Issue**: See [the command line tutorial](cl_tutorial.md).

**Inference on SWE-bench**: Run SWE-agent on [SWE-bench Lite](https://www.swebench.com/lite.html) and generate patches.

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

## 🧪 Evaluation <a name="evaluation"></a>
This step is only available for issues from the SWE-bench set. To evaluate generated pull requests:
```bash
cd evaluation/
./run_eval.sh <predictions_path>
```
Replace `<predictions_path>` with the path to the model's predictions, which should be generated from the *Inference* step. The `<predictions_path>` arguments should look like `../trajectories/<username>/<model>-<dataset>-<hyperparams>/all_preds.jsonl`
* See the [`evaluation/`](https://github.com/princeton-nlp/SWE-agent/tree/main/evaluation/) folder for details about how evaluation works.