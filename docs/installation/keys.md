# Models and API keys

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

!!! tip "Models"
    Some more information about the available models in our [usage FAQ](../usage/usage_faq.md).
