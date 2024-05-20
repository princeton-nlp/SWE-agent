# Adding your API keys

Create a `keys.cfg` file at the root of this repository and populate it with your API keys.

```
GITHUB_TOKEN: 'GitHub Token for access to private repos'  # <-- delete line if not used
OPENAI_API_KEY: 'OpenAI API Key Here if using OpenAI Model'
ANTHROPIC_API_KEY: 'Anthropic API Key Here if using Anthropic Model'
TOGETHER_API_KEY: 'Together API Key Here if using Together Model'
AZURE_OPENAI_API_KEY: 'Azure OpenAI API Key Here if using Azure OpenAI Model'
AZURE_OPENAI_ENDPOINT: 'Azure OpenAI Endpoint Here if using Azure OpenAI Model'
AZURE_OPENAI_DEPLOYMENT: 'Azure OpenAI Deployment Here if using Azure OpenAI Model'
AZURE_OPENAI_API_VERSION: 'Azure OpenAI API Version Here if using Azure OpenAI Model'
OPENAI_API_BASE_URL: 'LM base URL here if using Local or alternative api Endpoint'
```  

See the following links for tutorials on obtaining [Anthropic](https://docs.anthropic.com/claude/reference/getting-started-with-the-api), [OpenAI](https://platform.openai.com/docs/quickstart/step-2-set-up-your-api-key), and [Github](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) tokens.