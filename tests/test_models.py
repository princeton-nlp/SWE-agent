from unittest.mock import MagicMock, Mock, patch
import pytest
from sweagent.agent.models import OpenAIModel, ModelArguments, AnthropicModel, OllamaModel, HumanModel

TEST_HISTORY = [
    {
        "role": "system",
        "content": "Hello, how are you?"
    }
]


@pytest.fixture
def mock_openai_response():
    choice = Mock(message=Mock(content="test"))
    usage = Mock(prompt_tokens=10, completion_tokens=10)
    return Mock(choices=[choice], usage=usage)


@pytest.fixture
def mock_anthropic2_response():
    return Mock(
        id="test",
        completion="Hello. I'm fine.",
        model="claude-haiku",
        stop_reason=None,
        type="completion",
        usage=Mock(input_tokens=10, output_tokens=10)
    )


@pytest.fixture
def mock_anthropic3_response():
    return Mock(
        id="test",
        content=[Mock(type="text", text="Hello, I'm fine")],
        model="claude-haiku",
        role="assistant",
        stop_reason=None,
        stop_sequence=None,
        type="message",
        usage=Mock(input_tokens=10, output_tokens=10)
    )


@pytest.fixture
def mock_ollama_response():
    return {
        "prompt_eval_count": 10,
        "eval_count": 10,
        "message": {
            "content": "Hello. I'm fine."
        }
    }


def split_claude_model_by_version():
    claude2, claude3 = [], []
    for model_name in AnthropicModel.MODELS:
        if model_name == "claude-instant" or model_name.startswith("claude-2"):
            claude2.append(model_name)
        else:
            claude3.append(model_name)

    for short, full in AnthropicModel.SHORTCUTS.items():
        if full.startswith("claude-2"):
            claude2.append(short)
        else:
            claude3.append(short)

    return claude2, claude3


CLAUDE2_MODELS, CLAUDE3_MODELS = split_claude_model_by_version()


@pytest.mark.parametrize("model_name", list(OpenAIModel.MODELS) + list(OpenAIModel.SHORTCUTS))
def test_openai_model(model_name, mock_openai_response):
    with patch("sweagent.agent.models.config.Config"), \
            patch("sweagent.agent.models.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response

        model_args = ModelArguments(model_name)
        model = OpenAIModel(model_args, [])
        model.query(TEST_HISTORY)


@pytest.mark.parametrize("model_name", CLAUDE2_MODELS)
def test_anthropic2_model(model_name, mock_anthropic2_response):
    with patch("sweagent.agent.models.config.Config"), \
            patch("sweagent.agent.models.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.completions.create.return_value = mock_anthropic2_response
        mock_anthropic.return_value.count_tokens.return_value = 10

        model_args = ModelArguments(model_name)
        model = AnthropicModel(model_args, [])
        model.query(TEST_HISTORY)


@pytest.mark.parametrize("model_name", CLAUDE3_MODELS)
def test_anthropic3_model(model_name, mock_anthropic3_response):
    with patch("sweagent.agent.models.config.Config"), \
            patch("sweagent.agent.models.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = mock_anthropic3_response

        model_args = ModelArguments(model_name)
        model = AnthropicModel(model_args, [])
        model.query(TEST_HISTORY)


def test_ollama_model(mock_ollama_response):
    with patch("sweagent.agent.models.config.Config"), patch("sweagent.agent.models.OllamaClient") as mock_ollama:
        mock_ollama.return_value.chat.return_value = mock_ollama_response

        model_args = ModelArguments("ollama:llama2")
        model = OllamaModel(model_args, [])
        model.query(TEST_HISTORY)


def test_human_model():
    with patch("sweagent.agent.models.config.Config"), patch("builtins.input", return_value="Hello, I'm fine."):
        model_args = ModelArguments("human")
        model = HumanModel(model_args, [])
        model.query(TEST_HISTORY)

