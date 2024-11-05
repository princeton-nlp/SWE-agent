from __future__ import annotations

import copy
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, fields
from pathlib import Path

import together
from anthropic import AI_PROMPT, HUMAN_PROMPT, Anthropic, AnthropicBedrock
from groq import Groq
from openai import AzureOpenAI, BadRequestError, OpenAI
from pydantic import BaseModel as PydanticBaseModel
from simple_parsing.helpers.serialization.serializable import Serializable
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from sweagent.agent.commands import Command
from sweagent.utils.config import keys_config
from sweagent.utils.log import get_logger

logger = get_logger("lm", emoji="🤖")

_MAX_RETRIES = int(keys_config.get("SWE_AGENT_MODEL_MAX_RETRIES", 10))


# todo: Separate out human model and replay model?
class ModelConfig(PydanticBaseModel):
    """Arguments configuring the model and its behavior."""

    # Name of the model to use
    name: str = "gpt4"
    # Cost limit for every instance (task)
    per_instance_cost_limit: float = 0.0
    # Total cost limit
    total_cost_limit: float = 0.0
    # Sampling temperature
    temperature: float = 1.0
    # Sampling top-p
    top_p: float = 1.0
    # Path to replay file when using the replay model
    replay_path: str | None = None
    # Host URL when using Ollama model
    host_url: str = "localhost:11434"


@dataclass
class APIStats(Serializable):
    total_cost: float = 0
    instance_cost: float = 0
    tokens_sent: int = 0
    tokens_received: int = 0
    api_calls: int = 0

    def __add__(self, other):
        if not isinstance(other, APIStats):
            msg = "Can only add APIStats with APIStats"
            raise TypeError(msg)

        return APIStats(
            **{field.name: getattr(self, field.name) + getattr(other, field.name) for field in fields(self)},
        )

    def replace(self, other):
        if not isinstance(other, APIStats):
            msg = "Can only replace APIStats with APIStats"
            raise TypeError(msg)

        return APIStats(**{field.name: getattr(other, field.name) for field in fields(self)})


class ContextWindowExceededError(Exception):
    pass


class CostLimitExceededError(Exception):
    pass


class BaseModel:
    MODELS = {}
    SHORTCUTS = {}

    def __init__(self, args: ModelConfig, commands: list[Command]):
        self.args = args
        self.commands = commands
        self.model_metadata = {}
        self.stats = APIStats()

        # Map `model_name` to API-compatible name `api_model`
        self.api_model = self.SHORTCUTS[self.args.name] if self.args.name in self.SHORTCUTS else self.args.name

        # Map model name to metadata (cost, context info)
        MODELS = {
            **{dest: self.MODELS[src] for dest, src in self.SHORTCUTS.items()},
            **self.MODELS,
        }
        if args.name in MODELS:
            self.model_metadata = MODELS[args.name]
        elif args.name.startswith("ft:"):
            ft_model = args.name.split(":")[1]
            self.model_metadata = MODELS[ft_model]
        elif args.name.startswith("ollama:"):
            self.api_model = args.name.split("ollama:", 1)[1]
            self.model_metadata = self.MODELS[self.api_model]
        elif args.name.startswith("azure:"):
            azure_model = args.name.split("azure:", 1)[1]
            self.model_metadata = MODELS[azure_model]
        elif args.name.startswith("bedrock:"):
            self.api_model = args.name.split("bedrock:", 1)[1]
            self.model_metadata = MODELS[self.api_model]
        elif args.name.startswith("groq:"):
            self.api_model = args.name.split("groq:", 1)[1]
            self.model_metadata = MODELS[self.api_model]
        else:
            msg = f"Unregistered model ({args.name}). Add model name to MODELS metadata to {self.__class__}"
            raise ValueError(msg)

    def reset_stats(self, other: APIStats | None = None):
        if other is None:
            self.stats = APIStats(total_cost=self.stats.total_cost)
            logger.info("Resetting model stats")
        else:
            # Make sure to copy the stats to avoid modifying the original
            self.stats = copy.deepcopy(other)

    def update_stats(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculates the cost of a response from the openai API.

        Args:
        input_tokens (int): The number of tokens in the prompt.
        output_tokens (int): The number of tokens in the response.

        Returns:
        float: The cost of the response.
        """
        # Calculate cost and update cost related fields
        cost = (
            self.model_metadata["cost_per_input_token"] * input_tokens
            + self.model_metadata["cost_per_output_token"] * output_tokens
        )
        self.stats.total_cost += cost
        self.stats.instance_cost += cost
        self.stats.tokens_sent += input_tokens
        self.stats.tokens_received += output_tokens
        self.stats.api_calls += 1

        # Log updated cost values to std. err
        logger.debug(
            f"input_tokens={input_tokens:,}, "
            f"output_tokens={output_tokens:,}, "
            f"instance_cost={self.stats.instance_cost:.2f}, "
            f"cost={cost:.2f}",
        )
        logger.debug(
            f"total_tokens_sent={self.stats.tokens_sent:,}, "
            f"total_tokens_received={self.stats.tokens_received:,}, "
            f"total_cost={self.stats.total_cost:.2f}, "
            f"total_api_calls={self.stats.api_calls:,}",
        )

        # Check whether total cost or instance cost limits have been exceeded
        if 0 < self.args.total_cost_limit <= self.stats.total_cost:
            logger.warning(f"Cost {self.stats.total_cost:.2f} exceeds limit {self.args.total_cost_limit:.2f}")
            msg = "Total cost limit exceeded"
            raise CostLimitExceededError(msg)

        if 0 < self.args.per_instance_cost_limit <= self.stats.instance_cost:
            logger.warning(f"Cost {self.stats.instance_cost:.2f} exceeds limit {self.args.per_instance_cost_limit:.2f}")
            msg = "Instance cost limit exceeded"
            raise CostLimitExceededError(msg)
        return cost

    def query(self, history: list[dict[str, str]]) -> str:
        msg = "Use a subclass of BaseModel"
        raise NotImplementedError(msg)

    def history_to_messages(
        self,
        history: list[dict[str, str]],
        is_demonstration: bool = False,
    ) -> str | list[dict[str, str]]:
        msg = "Use a subclass of BaseModel"
        raise NotImplementedError(msg)


class OpenAIModel(BaseModel):
    MODELS = {
        "gpt-3.5-turbo-0125": {
            "max_context": 16_385,
            "cost_per_input_token": 5e-07,
            "cost_per_output_token": 1.5e-06,
        },
        "gpt-3.5-turbo-1106": {
            "max_context": 16_385,
            "cost_per_input_token": 1.5e-06,
            "cost_per_output_token": 2e-06,
        },
        "gpt-3.5-turbo-16k-0613": {
            "max_context": 16_385,
            "cost_per_input_token": 1.5e-06,
            "cost_per_output_token": 2e-06,
        },
        "gpt-4-32k-0613": {
            "max_context": 32_768,
            "cost_per_input_token": 6e-05,
            "cost_per_output_token": 0.00012,
        },
        "gpt-4-0613": {
            "max_context": 8_192,
            "cost_per_input_token": 3e-05,
            "cost_per_output_token": 6e-05,
        },
        "gpt-4-1106-preview": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
        "gpt-4-0125-preview": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
        "gpt-4-turbo-2024-04-09": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
        "gpt-4o-2024-05-13": {
            "max_context": 128_000,
            "cost_per_input_token": 5e-06,
            "cost_per_output_token": 15e-06,
        },
        "gpt-4o-mini-2024-07-18": {
            "max_context": 128_000,
            "cost_per_input_token": 1.5e-07,
            "cost_per_output_token": 6e-07,
        },
        "o1-preview-2024-09-12": {
            "max_context": 128_000,
            "cost_per_input_token": 15e-06,
            "cost_per_output_token": 60e-06,
        },
        "o1-mini-2024-09-12": {
            "max_context": 128_000,
            "cost_per_input_token": 3e-6,
            "cost_per_output_token": 12e-6,
        },
    }

    SHORTCUTS = {
        "gpt3": "gpt-3.5-turbo-1106",
        "gpt3-legacy": "gpt-3.5-turbo-16k-0613",
        "gpt4": "gpt-4-1106-preview",
        "gpt4-legacy": "gpt-4-0613",
        "gpt4-0125": "gpt-4-0125-preview",
        "gpt3-0125": "gpt-3.5-turbo-0125",
        "gpt4-turbo": "gpt-4-turbo-2024-04-09",
        "gpt4o": "gpt-4o-2024-05-13",
        "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
        "gpt4omini": "gpt-4o-mini-2024-07-18",
        "o1": "o1-preview-2024-09-12",
        "o1-mini": "o1-mini-2024-09-12",
    }

    def __init__(self, args: ModelConfig, commands: list[Command]):
        super().__init__(args, commands)

        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

        self._setup_client()

    def _setup_client(self):
        if self.args.name.startswith("azure"):
            logger.warning(
                "The --model CLI argument is ignored when using the Azure GPT endpoint. "
                "The model is determined by the AZURE_OPENAI_DEPLOYMENT key/"
                "environment variable (this might change in the future).",
            )
            self.api_model = keys_config["AZURE_OPENAI_DEPLOYMENT"]
            self.client = AzureOpenAI(
                api_key=keys_config["AZURE_OPENAI_API_KEY"],
                azure_endpoint=keys_config["AZURE_OPENAI_ENDPOINT"],
                api_version=keys_config.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            )
        else:
            api_base_url: str | None = keys_config.get("OPENAI_API_BASE_URL", None)
            self.client = OpenAI(api_key=keys_config["OPENAI_API_KEY"], base_url=api_base_url)

    def history_to_messages(
        self,
        history: list[dict[str, str]],
        is_demonstration: bool = False,
    ) -> str | list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
            return "\n".join([entry["content"] for entry in history])
        # Return history components with just role, content fields
        return [{k: v for k, v in entry.items() if k in ["role", "content"]} for entry in history]

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(_MAX_RETRIES),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, history: list[dict[str, str]]) -> str:
        """
        Query the OpenAI API with the given `history` and return the response.
        """
        try:
            # Perform OpenAI API call
            response = self.client.chat.completions.create(
                messages=self.history_to_messages(history),
                model=self.api_model,
                temperature=self.args.temperature,
                top_p=self.args.top_p,
            )
        except BadRequestError:
            msg = f"Context window ({self.model_metadata['max_context']} tokens) exceeded"
            raise ContextWindowExceededError(msg)
        # Calculate + update costs, return response
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        self.update_stats(input_tokens, output_tokens)
        return response.choices[0].message.content


class DeepSeekModel(OpenAIModel):
    MODELS = {
        "deepseek-coder": {
            "max_context": 32_000,
            "cost_per_input_token": 1.4e-07,
            "cost_per_output_token": 2.8e-07,
        },
    }
    SHORTCUTS = {}

    def _setup_client(self) -> None:
        api_base_url: str = keys_config["DEEPSEEK_API_BASE_URL"]
        self.client = OpenAI(api_key=keys_config["DEEPSEEK_API_KEY"], base_url=api_base_url)


class GroqModel(OpenAIModel):
    MODELS = {
        "llama3-8b-8192": {
            "max_context": 8192,
            "cost_per_input_token": 5e-08,
            "cost_per_output_token": 8e-08,
        },
        "llama3-70b-8192": {
            "max_context": 8192,
            "cost_per_input_token": 5.9e-07,
            "cost_per_output_token": 7.9e-07,
        },
        "llama-guard-3-8b": {
            "max_context": 8192,
            "cost_per_input_token": 0,
            "cost_per_output_token": 0,
        },
        "llama-3.1-8b-instant": {
            "max_context": 131_072,
            "cost_per_input_token": 0,
            "cost_per_output_token": 0,
        },
        "llama-3.1-70b-versatile": {
            "max_context": 131_072,
            "cost_per_input_token": 0,
            "cost_per_output_token": 0,
        },
        "gemma2-9b-it": {
            "max_context": 8192,
            "cost_per_input_token": 2e-07,
            "cost_per_output_token": 2e-07,
        },
        "gemma-7b-it": {
            "max_context": 8192,
            "cost_per_input_token": 5e-08,
            "cost_per_output_token": 5e-08,
        },
        "mixtral-8x7b-32768": {
            "max_context": 32_768,
            "cost_per_input_token": 2.4e-07,
            "cost_per_output_token": 2.8e-07,
        },
    }

    SHORTCUTS = {
        "groq/llama8": "llama3-8b-8192",
        "groq/llama70": "llama3-70b-8192",
        "groq/llamaguard8": "llama-guard-3-8b",
        "groq/llamainstant8": "llama-3.1-8b-instant",
        "groq/llamaversatile70": "llama-3.1-70b-versatile",
        "groq/gemma9it": "gemma2-9b-it",
        "groq/gemma7it": "gemma-7b-it",
        "groq/mixtral8x7": "mixtral-8x7b-32768",
    }

    def _setup_client(self) -> None:
        self.client = Groq(
            api_key=keys_config["GROQ_API_KEY"],
        )


class AnthropicModel(BaseModel):
    MODELS = {
        "claude-instant": {
            "max_context": 100_000,
            "cost_per_input_token": 1.63e-06,
            "cost_per_output_token": 5.51e-06,
        },
        "claude-2.0": {
            "max_context": 100_000,
            "cost_per_input_token": 1.102e-05,
            "cost_per_output_token": 3.268e-05,
        },
        "claude-2.1": {
            "max_context": 100_000,
            "cost_per_input_token": 1.102e-05,
            "cost_per_output_token": 3.268e-05,
        },
        "claude-3-opus-20240229": {
            "max_context": 200_000,
            "max_tokens": 4096,  # Max tokens to generate for Claude 3 models
            "cost_per_input_token": 1.5e-05,
            "cost_per_output_token": 7.5e-05,
        },
        "claude-3-sonnet-20240229": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 3e-06,
            "cost_per_output_token": 1.5e-05,
        },
        "claude-3-5-sonnet-20240620": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 3e-06,
            "cost_per_output_token": 1.5e-05,
        },
        "claude-3-haiku-20240307": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 2.5e-07,
            "cost_per_output_token": 1.25e-06,
        },
    }

    SHORTCUTS = {
        "claude-2": "claude-2.1",
        "claude-opus": "claude-3-opus-20240229",
        "claude-sonnet": "claude-3-sonnet-20240229",
        "claude-haiku": "claude-3-haiku-20240307",
        "claude-sonnet-3.5": "claude-3-5-sonnet-20240620",
    }

    def __init__(self, args: ModelConfig, commands: list[Command]):
        super().__init__(args, commands)

        # Set Anthropic key
        self.api = Anthropic(api_key=keys_config["ANTHROPIC_API_KEY"])

    def history_to_messages(
        self,
        history: list[dict[str, str]],
        is_demonstration: bool = False,
    ) -> str | list[dict[str, str]]:
        """
        Create `prompt` by filtering out all keys except for role/content per `history` turn
        Reference: https://docs.anthropic.com/claude/reference/complete_post
        """
        return anthropic_history_to_messages(self, history, is_demonstration)

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(_MAX_RETRIES),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, history: list[dict[str, str]]) -> str:
        """
        Query the Anthropic API with the given `history` and return the response.
        """
        return anthropic_query(self, history)


class BedrockModel(BaseModel):
    MODELS = {
        "anthropic.claude-instant-v1": {
            "max_context": 100_000,
            "max_tokens_to_sample": 4096,
            "cost_per_input_token": 8e-07,
            "cost_per_output_token": 2.4e-06,
        },
        "anthropic.claude-v2": {
            "max_context": 100_000,
            "max_tokens_to_sample": 4096,
            "cost_per_input_token": 8e-06,
            "cost_per_output_token": 2.4e-05,
        },
        "anthropic.claude-v2:1": {
            "max_context": 100_000,
            "max_tokens": 4096,
            "cost_per_input_token": 8e-06,
            "cost_per_output_token": 2.4e-05,
        },
        "anthropic.claude-3-opus-20240229-v1:0": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 1.5e-05,
            "cost_per_output_token": 7.5e-05,
        },
        "anthropic.claude-3-sonnet-20240229-v1:0": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 3e-06,
            "cost_per_output_token": 1.5e-05,
        },
        "anthropic.claude-3-haiku-20240307-v1:0": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 2.5e-07,
            "cost_per_output_token": 1.25e-06,
        },
    }

    def __init__(self, args: ModelConfig, commands: list[Command]):
        super().__init__(args, commands)

        # Extract provider from model ID
        # https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html
        self.model_provider = self.api_model.split(".")[0]
        if self.model_provider == "anthropic":
            # Note: this assumes AWS credentials are already configured.
            # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
            self.api = AnthropicBedrock()
        elif self.model_provider in ["ai21", "amazon", "cohere", "meta", "mistral"]:
            msg = f"{self.api_model} is not supported!"
            raise NotImplementedError(msg)
        else:
            msg = f"Provider {self.model_provider} is not supported by Amazon Bedrock!"
            raise ValueError(msg)

    def history_to_messages(
        self,
        history: list[dict[str, str]],
        is_demonstration: bool = False,
    ) -> str | list[dict[str, str]]:
        """
        Create `prompt` from the history of messages
        """
        if self.model_provider == "anthropic":
            return anthropic_history_to_messages(self, history, is_demonstration)
        else:
            msg = f"{self.api_model} is not supported!"
            raise NotImplementedError(msg)

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(_MAX_RETRIES),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, history: list[dict[str, str]]) -> str:
        """
        Query Amazon Bedrock with the given `history` and return the response.
        """
        if self.model_provider == "anthropic":
            return anthropic_query(self, history)
        else:
            msg = f"{self.api_model} is not supported!"
            raise NotImplementedError(msg)


def anthropic_history_to_messages(
    model: AnthropicModel | BedrockModel,
    history: list[dict[str, str]],
    is_demonstration: bool = False,
) -> str | list[dict[str, str]]:
    """
    Create `prompt` by filtering out all keys except for role/content per `history` turn
    Reference: https://docs.anthropic.com/claude/reference/complete_post
    """
    # Preserve behavior for older models
    if model.api_model in ["claude-instant", "claude-2.0"] or (
        isinstance(model, BedrockModel) and model.api_model in ["anthropic.claude-instant-v1", "anthropic.claude-v2"]
    ):
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
        # Map history to Claude format
        prompt = "\n\n"
        for entry in history:
            if entry["role"] in {"user", "system"}:
                prompt += f'{HUMAN_PROMPT} {entry["content"]}\n\n'
            elif entry["role"] == "assistant":
                prompt += f'{AI_PROMPT} {entry["content"]}\n\n'
        prompt += AI_PROMPT
        return prompt

    # Remove system messages if it is a demonstration
    if is_demonstration:
        history = [entry for entry in history if entry["role"] != "system"]
        return "\n".join([entry["content"] for entry in history])

    # Return history components with just role, content fields (no system message)
    messages = [
        {k: v for k, v in entry.items() if k in ["role", "content"]} for entry in history if entry["role"] != "system"
    ]
    compiled_messages = []  # Combine messages from the same role
    last_role = None
    for message in reversed(messages):
        if last_role == message["role"]:
            compiled_messages[-1]["content"] = message["content"] + "\n" + compiled_messages[-1]["content"]
        else:
            compiled_messages.append(message)
        last_role = message["role"]
    compiled_messages = list(reversed(compiled_messages))
    # Replace any empty content values with a "(No output)"
    for message in compiled_messages:
        if message["content"].strip() == "":
            message["content"] = "(No output)"
    return compiled_messages


def anthropic_query(model: AnthropicModel | BedrockModel, history: list[dict[str, str]]) -> str:
    """
    Query the Anthropic API with the given `history` and return the response.
    """
    # Preserve behavior for older models
    if model.api_model in ["claude-instant", "claude-2.0", "claude-2.1"] or (
        isinstance(model, BedrockModel) and model.api_model in ["anthropic.claude-instant-v1", "anthropic.claude-v2"]
    ):
        # Perform Anthropic API call
        prompt = anthropic_history_to_messages(model, history)
        if isinstance(model, BedrockModel):
            # Use a dummy Anthropic client since count_tokens
            # is not available in AnthropicBedrock
            # https://github.com/anthropics/anthropic-sdk-python/issues/353
            input_tokens = Anthropic().count_tokens(prompt)
        else:
            input_tokens = model.api.count_tokens(prompt)
        completion = model.api.completions.create(
            model=model.api_model,
            prompt=prompt,
            max_tokens_to_sample=model.model_metadata["max_context"] - input_tokens
            if isinstance(model, Anthropic)
            else model.model_metadata["max_tokens_to_sample"],
            temperature=model.args.temperature,
            top_p=model.args.top_p,
        )
        # Calculate + update costs, return response
        response = completion.completion
        if isinstance(model, BedrockModel):
            output_tokens = Anthropic().count_tokens(response)
        else:
            output_tokens = model.api.count_tokens(response)
        model.update_stats(input_tokens, output_tokens)
        return response

    # Get system message(s)
    system_message = "\n".join([entry["content"] for entry in history if entry["role"] == "system"])
    messages = anthropic_history_to_messages(model, history)

    # Perform Anthropic API call
    response = model.api.messages.create(
        messages=messages,
        max_tokens=model.model_metadata["max_tokens"],
        model=model.api_model,
        temperature=model.args.temperature,
        top_p=model.args.top_p,
        system=system_message,
    )

    # Calculate + update costs, return response
    model.update_stats(response.usage.input_tokens, response.usage.output_tokens)
    return "\n".join([x.text for x in response.content])


class OllamaModel(BaseModel):
    MODELS = defaultdict(
        lambda: {
            "max_context": 128_000,
            "cost_per_input_token": 0,
            "cost_per_output_token": 0,
        },
    )

    def __init__(self, args: ModelConfig, commands: list[Command]):
        super().__init__(args, commands)
        from ollama import Client

        self.client = Client(host=args.host_url)

    def history_to_messages(
        self,
        history: list[dict[str, str]],
        is_demonstration: bool = False,
    ) -> str | list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
            return "\n".join([entry["content"] for entry in history])
        # Return history components with just role, content fields
        return [{k: v for k, v in entry.items() if k in ["role", "content"]} for entry in history]

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(_MAX_RETRIES),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, history: list[dict[str, str]]) -> str:
        """
        Query the Ollama API with the given `history` and return the response.
        """
        response = self.client.chat(
            model=self.api_model,
            messages=self.history_to_messages(history),
            options={
                "temperature": self.args.temperature,
                "top_p": self.args.top_p,
            },
        )
        # Calculate + update costs, return response
        if "prompt_eval_count" in response:
            input_tokens = response["prompt_eval_count"]
        else:
            logger.warning(
                "Prompt eval count not found in response. Using 0. "
                "This might be because the prompt has been cached. "
                "See https://github.com/princeton-nlp/SWE-agent/issues/44 "
                "and https://github.com/ollama/ollama/issues/3427.",
            )
            input_tokens = 0
        output_tokens = response["eval_count"]
        self.update_stats(input_tokens, output_tokens)
        return response["message"]["content"]


class TogetherModel(BaseModel):
    # Check https://docs.together.ai/docs/inference-models for model names, context
    # Check https://www.together.ai/pricing for pricing
    MODELS = {
        "meta-llama/Llama-2-13b-chat-hf": {
            "max_context": 4096,
            "cost_per_input_token": 2.25e-07,
            "cost_per_output_token": 2.25e-07,
        },
        "meta-llama/Llama-2-70b-chat-hf": {
            "max_context": 4096,
            "cost_per_input_token": 9e-07,
            "cost_per_output_token": 9e-07,
        },
        "mistralai/Mistral-7B-Instruct-v0.2": {
            "max_context": 32768,
            "cost_per_input_token": 2e-07,
            "cost_per_output_token": 2e-07,
        },
        "togethercomputer/RedPajama-INCITE-7B-Chat": {
            "max_context": 2048,
            "cost_per_input_token": 2e-07,
            "cost_per_output_token": 2e-07,
        },
        "mistralai/Mixtral-8x7B-Instruct-v0.1": {
            "max_context": 32768,
            "cost_per_input_token": 6e-07,
            "cost_per_output_token": 6e-07,
        },
    }

    SHORTCUTS = {
        "llama13b": "meta-llama/Llama-2-13b-chat-hf",
        "llama70b": "meta-llama/Llama-2-70b-chat-hf",
        "mistral7b": "mistralai/Mistral-7B-Instruct-v0.2",
        "mixtral8x7b": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "redpajama7b": "togethercomputer/RedPajama-INCITE-7B-Chat",
    }

    def __init__(self, args: ModelConfig, commands: list[Command]):
        super().__init__(args, commands)
        assert together.version >= "1.1.0", "Please upgrade to Together SDK v1.1.0 or later."

        # Set Together key
        together.api_key = keys_config["TOGETHER_API_KEY"]

    def history_to_messages(self, history: list[dict[str, str]], is_demonstration: bool = False) -> str:
        """
        Create `prompt` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
        # Map history to TogetherAI format
        mapping = {"user": "human", "assistant": "bot", "system": "bot"}
        prompt = [f'<{mapping[d["role"]]}>: {d["content"]}' for d in history]
        prompt = "\n".join(prompt)
        return f"{prompt}\n<bot>:"

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(_MAX_RETRIES),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, history: list[dict[str, str]]) -> str:
        """
        Query the Together API with the given `history` and return the response.
        """
        # Perform Together API call
        prompt = self.history_to_messages(history)
        # Anthropic's count_tokens is convenient because it caches and utilizes huggingface/tokenizers, so we will use.
        max_tokens_to_sample = self.model_metadata["max_context"] - Anthropic().count_tokens(prompt)
        completion = together.Complete.create(
            model=self.api_model,
            prompt=prompt,
            max_tokens=max_tokens_to_sample,
            stop=["<human>"],
            temperature=self.args.temperature,
            top_p=self.args.top_p,
        )
        # Calculate + update costs, return response
        response = completion["choices"][0]["text"].split("<human>")[0]
        input_tokens = completion["usage"]["prompt_tokens"]
        output_tokens = completion["usage"]["completion_tokens"]
        self.update_stats(input_tokens, output_tokens)
        return response


def _history_to_messages(history: list[dict[str, str]], is_demonstration: bool = False) -> str | list[dict[str, str]]:
    """
    Create `messages` by filtering out all keys except for role/content per `history` turn
    """
    if is_demonstration:
        history = [entry for entry in history if entry["role"] != "system"]
        return "\n".join([entry["content"] for entry in history])
        # Return history components with just role, content fields
    return [{k: v for k, v in entry.items() if k in ["role", "content"]} for entry in history]


class HumanModel(BaseModel):
    MODELS = {"human": {}}

    def __init__(self, args: ModelConfig, commands: list[Command]):
        super().__init__(args, commands)

        # Determine which commands require multi-line input
        self.multi_line_command_endings = {
            command.name: command.end_name for command in commands if command.end_name is not None
        }

    def history_to_messages(
        self,
        history: list[dict[str, str]],
        is_demonstration: bool = False,
    ) -> str | list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        return _history_to_messages(history, is_demonstration)

    def query(self, history: list[dict[str, str]], action_prompt: str = "> ") -> str:
        """
        Logic for handling user input to pass to SWEEnv
        """
        action = input(action_prompt)
        command_name = action.split()[0] if action.strip() else ""

        # Special handling for multi-line input actions (i.e. edit)
        if command_name in self.multi_line_command_endings:
            buffer = [action]
            end_keyword = self.multi_line_command_endings[command_name]
            while True:
                action = input("... ")
                buffer.append(action)
                if action.rstrip() == end_keyword:
                    # Continue reading input until terminating keyword inputted
                    break
            action = "\n".join(buffer)
        elif action.strip() == "start_multiline_command":  # do arbitrary multi-line input
            buffer = []
            while True:
                action = input("... ")
                if action.rstrip() == "end_multiline_command":
                    break
                buffer.append(action)
            action = "\n".join(buffer)
        return action


class HumanThoughtModel(HumanModel):
    MODELS = {"human_thought": {}}

    def query(self, history: list[dict[str, str]]) -> str:
        """
        Logic for handling user input (both thought + action) to pass to SWEEnv
        """
        thought_all = ""
        thought = input("Thought (end w/ END_THOUGHT): ")
        while True:
            if "END_THOUGHT" in thought:
                thought = thought.split("END_THOUGHT")[0]
                thought_all += thought
                break
            thought_all += thought
            thought = input("... ")

        action = super().query(history, action_prompt="Action: ")

        return f"{thought_all}\n```\n{action}\n```"


class ReplayModel(BaseModel):
    MODELS = {"replay": {}}

    def __init__(self, args: ModelConfig, commands: list[Command]):
        super().__init__(args, commands)

        if self.args.replay_path is None or not Path(self.args.replay_path).exists():
            msg = "--replay_path must point to a file that exists to run a replay policy"
            raise ValueError(msg)

        self.replays = [
            list(json.loads(x).values())[0] for x in Path(self.args.replay_path).read_text().splitlines(keepends=True)
        ]
        self.replay_idx = 0
        self.action_idx = 0

    def _next_replay(self) -> None:
        """Called after last action"""
        self.replay_idx += 1
        self.action_idx = 0

    def query(self, history: list[dict[str, str]]) -> str:
        """
        Logic for tracking which replay action to pass to SWEEnv
        """
        actions = self.replays[self.replay_idx]
        try:
            action = actions[self.action_idx]
        except IndexError:
            msg = (
                "This seems to be an incomplete trajectory. "
                "We reached the end of it, but `submit` was not called. "
                "Calling it now."
            )
            logger.warning(msg)
            action = "```\nsubmit\n```"

        self.action_idx += 1

        # Assuming `submit` is always last action of replay trajectory
        if action == "submit":
            self._next_replay()

        return action

    def history_to_messages(self, history: list[dict[str, str]], *args, **kwargs) -> str | list[dict[str, str]]:
        return _history_to_messages(history, is_demonstration=True)


class InstantEmptySubmitTestModel(BaseModel):
    MODELS = {
        "instant_empty_submit": {
            "max_context": 100_000,
            "max_tokens_to_sample": 4096,
            "cost_per_input_token": 0,
            "cost_per_output_token": 0,
        }
    }

    def __init__(self, args: ModelConfig, commands: list[Command]):
        """This model immediately submits. Useful for testing purposes"""
        super().__init__(args, commands)
        self._action_idx = 0

    def query(self, history: list[dict[str, str]]) -> str:
        # Need to at least do _something_ to submit
        if self._action_idx == 0:
            self._action_idx = 1
            action = "DISCUSSION\nLet's reproduce the bug by creating a `reproduce.py` file.\n\n```\ncreate reproduce.py\n```\n"
        elif self._action_idx == 1:
            self._action_idx = 0
            action = "DISCUSSION\nThe task should be resolved, so let's submit the patch.\n\n```\nsubmit\n```\n"
        self.update_stats(0, 0)
        return action

    def history_to_messages(self, history: list[dict[str, str]], *args, **kwargs) -> list[dict[str, str]]:
        return history


def get_model(args: ModelConfig, commands: list[Command] | None = None):
    """
    Returns correct model object given arguments and commands
    """
    if commands is None:
        commands = []
    if args.name == "instant_empty_submit":
        return InstantEmptySubmitTestModel(args, commands)
    if args.name == "human":
        return HumanModel(args, commands)
    if args.name == "human_thought":
        return HumanThoughtModel(args, commands)
    if args.name == "replay":
        return ReplayModel(args, commands)
    elif (
        args.name.startswith("gpt")
        or args.name.startswith("ft:gpt")
        or args.name.startswith("azure:gpt")
        or args.name in OpenAIModel.SHORTCUTS
    ):
        return OpenAIModel(args, commands)
    elif args.name.startswith("claude"):
        return AnthropicModel(args, commands)
    elif args.name.startswith("bedrock"):
        return BedrockModel(args, commands)
    elif args.name.startswith("ollama"):
        return OllamaModel(args, commands)
    elif args.name.startswith("deepseek"):
        return DeepSeekModel(args, commands)
    elif args.name in TogetherModel.SHORTCUTS:
        return TogetherModel(args, commands)
    elif args.name in GroqModel.SHORTCUTS:
        return GroqModel(args, commands)
    elif args.name == "instant_empty_submit":
        return InstantEmptySubmitTestModel(args, commands)
    else:
        msg = f"Invalid model name: {args.name}"
        raise ValueError(msg)
