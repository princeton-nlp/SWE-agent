from __future__ import annotations

from pydantic import SecretStr

from sweagent.agent.models import GenericAPIModelConfig, get_model
from sweagent.types import History


def test_litellm_mock():
    model = get_model(
        GenericAPIModelConfig(
            name="anthropic/o1-preview",
            completion_kwargs={"mock_response": "Hello, world!"},
            api_key=SecretStr("dummy_key"),
        )
    )
    assert model.query(History([{"role": "user", "content": "Hello, world!"}])) == "Hello, world!"
