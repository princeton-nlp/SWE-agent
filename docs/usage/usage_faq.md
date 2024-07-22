# Usage FAQ

## What models are supported?

!!! note "Model support"
    Note that SWE-agent is currently unlikely to perform well with small or local models.

Models are configured in [`models.py`](https://github.com/princeton-nlp/SWE-agent/blob/main/sweagent/agent/models.py) (we're working on giving a complete list of model settings).

Here are some few examples:

```
gpt4
gpt4o
gpt4-turbo
claude-2
claude-opus
claude-sonnet
claude-haiku
claude-sonnet-3.5
deepseek-coder
azure:gpt4
```

### Ollama support

Models served with an ollama server can be used by specifying `--model` with `ollama:model_name` and `--host_url` to point to the url used to serve ollama (`http://localhost:11434` by default). See more details about using ollama [here](https://github.com/ollama/ollama/tree/main/docs).

```bash
python run.py --model_name ollama:deepseek-coder:6.7b-instruct \
  --host_url http://localhost:11434 \
  --data_path https://github.com/pvlib/pvlib-python/issues/1603 \
  --config_file config/default_from_url.yaml
```

### Qwen support

When using the Qwen model, it operates with an OpenAI-compatible API. Therefore, you need to specify `OPENAI_API_KEY` and `OPENAI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1` in the `keys.cfg` file. You can use the Qwen model by setting `--model_name` to `qwen`.

```bash
python run.py \
  --model_name qwen \
  --data_path https://github.com/SWE-agent/test-repo/issues/1 \
  --config_file config/default_from_url.yaml \
  --image_name=sweagent/swe-agent:latest
```

Refer to the documentation to obtain the `OPENAI_API_KEY`, see [here](https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope?spm=a2c4g.11186623.0.0.3eb75b785JJ2Nq).

### Models for testing

We also provide models for testing SWE-agent without spending any credits

* `HumanModel` and `HumandThoughtModel` will prompt for input from the user that stands in for the output of the LM. This can be used to create new [demonstrations](../config/demonstrations.md#manual).
* `ReplayModel` takes a trajectory as input and "replays it"
* `InstantEmptySubmitTestModel` will create an empty `reproduce.py` and then submit

### Debugging

* If you get `Error code: 404`, please check your configured keys, in particular
  whether you set `OPENAI_API_BASE_URL` correctly (if you're not using it, the
  line should be deleted or commented out).
  Also see [this issue](https://github.com/princeton-nlp/SWE-agent/issues/467)
  for reference.

{% include-markdown "../_footer.md" %}
