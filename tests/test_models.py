from unittest.mock import MagicMock, Mock, patch
from sweagent.agent.models import OpenAIModel, ModelArguments, AnthropicModel, OllamaModel, HumanModel
import pytest


@pytest.fixture
def openai_mock_client():
    model = Mock()
    reponse = Mock()
    choice = Mock()
    choice.message.content = "test"
    reponse.choices = [choice]
    reponse.usage.prompt_tokens = 10
    reponse.usage.completion_tokens = 10
    model.chat.completions.create = MagicMock(return_value=reponse)

    return model


def anthropic_return_value():
    return Mock(
        id="test",
        completion="Hello. I'm fine.",
        model="claude-haiku",
        stop_reason=None,
        type="completion"
    )


def ollama_return_value():
    return {
        "prompt_eval_count": 10,
        "eval_count": 10,
        "message": {
            "content": "Hello. I'm fine."
        }
    }


TEST_HISTORY = [
    {
        "role": "system",
        "content": "Hello, how are you?"
    }
]


def test_openai_model(openai_mock_client):
    for model_name in list(OpenAIModel.MODELS) + list(OpenAIModel.SHORTCUTS):
        TEST_MODEL_ARGUMENTS = ModelArguments(model_name)
        with patch("sweagent.agent.models.config.Config"), patch("sweagent.agent.models.OpenAI"):
            model = OpenAIModel(TEST_MODEL_ARGUMENTS, [])
        model.client = openai_mock_client
        model.query(TEST_HISTORY)


@patch("anthropic.resources.completions.Completions.create", return_value=anthropic_return_value())
def test_anthropic_model(mock):
    model_name = "claude"
    model_arguments = ModelArguments(model_name)
    with patch("sweagent.agent.models.config.Config"):
        model = AnthropicModel(model_arguments, [])

    model.query(TEST_HISTORY)


@patch("ollama.Client.chat", return_value=ollama_return_value())
def test_ollama_model(mock):
    model_arguments = ModelArguments("ollama:llama2")
    with patch("sweagent.agent.models.config.Config"):
        model = OllamaModel(model_arguments, [])

    model.query(TEST_HISTORY)


@patch("builtins.input", return_value="Hello, I'm fine.")
def test_human_model(mock):
    model_arguments = ModelArguments("human")
    with patch("sweagent.agent.models.config.Config"):
        model = HumanModel(model_arguments, [])

    model.query(TEST_HISTORY)
