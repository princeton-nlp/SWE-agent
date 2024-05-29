# Usage FAQ

## What models are supported?

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
```

### Ollama support

Models served with an ollama server can be used by specifying `--model` with `ollama:model_name` and `--host_url` to point to the url used to serve ollama (`http://localhost:11434` by default). See more details about using ollama [here](https://github.com/ollama/ollama/tree/main/docs).

```bash
python run.py --model_name ollama:deepseek-coder:6.7b-instruct \
  --host_url http://localhost:11434 \
  --data_path https://github.com/pvlib/pvlib-python/issues/1603 \
  --config_file config/default_from_url.yaml
```

### Models for testing

We also provide models for testing SWE-agent without spending any credits

* `HumanModel` and `HumandThoughtModel` will prompt for input from the user that stands in for the output of the LM. This can be used to create new [demonstrations](../config/demonstrations.md#manual).
* `ReplayModel` takes a trajectory as input and "replays it"
* `InstantEmptySubmitTestModel` will create an empty `reproduce.py` and then submit

{% include-markdown "../_footer.md" %}
