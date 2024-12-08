# Models and API keys

## Setting API keys

In order to access the LM of your choice (and to access private GitHub repositories), you need to supply the corresponding keys.

There are two options to do this:

1. Set the corresponding [environment variables](https://www.cherryservers.com/blog/how-to-set-list-and-manage-linux-environment-variables).
2. Create a `.env` file at the root of this repository. All of the variables defined there will take the place of environment variables.


Here's an example

```
# Remove the comment '#' in front of the line for all keys that you have set
# GITHUB_TOKEN='GitHub Token for access to private repos'
# OPENAI_API_KEY='OpenAI API Key Here if using OpenAI Model'
# ANTHROPIC_API_KEY='Anthropic API Key Here if using Anthropic Model'
# TOGETHER_API_KEY='Together API Key Here if using Together Model'
```

See the following links for tutorials on obtaining [Anthropic](https://docs.anthropic.com/en/api/getting-started), [OpenAI](https://platform.openai.com/docs/quickstart/step-2-set-up-your-api-key), and [Github](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) tokens.

## Supported models

We support all models supported by [litellm](https://github.com/BerriAI/litellm), see their list [here](https://docs.litellm.ai/docs/providers).

Here are a few options for `--agent.model.name`:

| Model | API key | Comment |
| ----- | ------- | ------- |
| `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` | Our recommended model |
| `gpt-4o` | `OPENAI_API_KEY` | |
| `o1-preview` | `OPENAI_API_KEY` | You might need to set temperature and sampling to the supported values. |

## Model options

See [our API docs](../reference/model_config.md) for more details.

### Models for testing

We also provide models for testing SWE-agent without spending any credits

* `HumanModel` and `HumanThoughtModel` will prompt for input from the user that stands in for the output of the LM. This can be used to create new [demonstrations](../config/demonstrations.md#manual).
* `ReplayModel` takes a trajectory as input and "replays it"
* `InstantEmptySubmitTestModel` will create an empty `reproduce.py` and then submit

### Debugging

* If you get `Error code: 404`, please check your configured keys, in particular
  whether you set `OPENAI_API_BASE_URL` correctly (if you're not using it, the
  line should be deleted or commented out).
  Also see [this issue](https://github.com/SWE-agent/SWE-agent/issues/467)
  for reference.