# Adding your API keys

In order to access the LM of your choice (and to access private GitHub repositories), you need to supply the corresponding keys.

There are two options to do this:

1. Set the corresponding [environment variables](https://www.cherryservers.com/blog/how-to-set-list-and-manage-linux-environment-variables).
2. Create a `keys.cfg` file at the root of this repository.

The following `keys.cfg` example shows you how the keys are named:

```
# Remove the comment '#' in front of the line for all keys that you have set
# GITHUB_TOKEN: 'GitHub Token for access to private repos'
# OPENAI_API_KEY: 'OpenAI API Key Here if using OpenAI Model'
# ANTHROPIC_API_KEY: 'Anthropic API Key Here if using Anthropic Model'
# TOGETHER_API_KEY: 'Together API Key Here if using Together Model'
# AZURE_OPENAI_API_KEY: 'Azure OpenAI API Key Here if using Azure OpenAI Model'
# AZURE_OPENAI_ENDPOINT: 'Azure OpenAI Endpoint Here if using Azure OpenAI Model'
# AZURE_OPENAI_DEPLOYMENT: 'Azure OpenAI Deployment Here if using Azure OpenAI Model'
# AZURE_OPENAI_API_VERSION: 'Azure OpenAI API Version Here if using Azure OpenAI Model'
# OPENAI_API_BASE_URL: 'LM base URL here if using Local or alternative api Endpoint'
```

See the following links for tutorials on obtaining [Anthropic](https://docs.anthropic.com/claude/reference/getting-started-with-the-api), [OpenAI](https://platform.openai.com/docs/quickstart/step-2-set-up-your-api-key), and [Github](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) tokens.

!!! tip "Models"
    Some more information about the available models in our [usage FAQ](../usage/usage_faq.md).
