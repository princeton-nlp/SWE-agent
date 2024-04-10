from tkinter.filedialog import Open
from unittest.mock import MagicMock, Mock, patch
from sweagent.agent.models import OpenAIModel, ModelArguments, AnthropicModel
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
