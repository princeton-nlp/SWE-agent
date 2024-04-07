import config
import json
import logging
import os
import together

from collections import defaultdict
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dataclasses import dataclass, fields
from openai import BadRequestError, OpenAI, AzureOpenAI
from simple_parsing.helpers import FrozenSerializable, Serializable
from sweagent.agent.commands import Command
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_not_exception_type,
)
from typing import Optional

logger = logging.getLogger("api_models")


@dataclass(frozen=True)
class ModelArguments(FrozenSerializable):
    model_name: str
    per_instance_cost_limit: float = 0.0
    total_cost_limit: float = 0.0
    temperature: float = 1.0
    top_p: float = 1.0
    replay_path: str = None
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
            raise TypeError("Can only add APIStats with APIStats")

        return APIStats(**{
            field.name: getattr(self, field.name) + getattr(other, field.name)
            for field in fields(self)
        })
    
    def replace(self, other):
        if not isinstance(other, APIStats):
            raise TypeError("Can only replace APIStats with APIStats")

        return APIStats(**{
            field.name: getattr(other, field.name)
            for field in fields(self)
        })


class ContextWindowExceededError(Exception):
    pass


class CostLimitExceededError(Exception):
    pass


class BaseModel:
    MODELS = {}
    SHORTCUTS = {}

    def __init__(self, args: ModelArguments, commands: list[Command]):
        self.args = args
        self.commands = commands
        self.model_metadata = {}
        self.stats = APIStats()

        # Map `model_name` to API-compatible name `api_model`
        self.api_model = (
            self.SHORTCUTS[self.args.model_name]
            if self.args.model_name in self.SHORTCUTS
            else self.args.model_name
        )

        # Map model name to metadata (cost, context info)
        MODELS = {
            **{dest: self.MODELS[src] for dest, src in self.SHORTCUTS.items()},
            **self.MODELS,
        }
        if args.model_name in MODELS:
            self.model_metadata = MODELS[args.model_name]
        elif args.model_name.startswith("ft:"):
            ft_model = args.model_name.split(":")[1]
            self.model_metadata = MODELS[ft_model]
        elif args.model_name.startswith("ollama:"):
            self.api_model = args.model_name.split('ollama:', 1)[1]
            self.model_metadata = self.MODELS[self.api_model]
        elif args.model_name.startswith("azure:"):
            azure_model = args.model_name.split("azure:", 1)[1]
            self.model_metadata = MODELS[azure_model]
        else:
            raise ValueError(f"Unregistered model ({args.model_name}). Add model name to MODELS metadata to {self.__class__}")

    def reset_stats(self, other: APIStats = None):
        if other is None:
            self.stats = APIStats(total_cost=self.stats.total_cost)
            logger.info("Resetting model stats")
        else:
            self.stats = other

    def update_stats(self, input_tokens, output_tokens):
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

        # Log updated cost values to std. out.
        logger.info(
            f"input_tokens={input_tokens:_}, "
            f"output_tokens={output_tokens:_}, "
            f"instance_cost={self.stats.instance_cost:.2f}, "
            f"cost={cost:.2f}"
        )
        logger.info(
            f"total_tokens_sent={self.stats.tokens_sent:_}, "
            f"total_tokens_received={self.stats.tokens_received:_}, "
            f"total_cost={self.stats.total_cost:.2f}, "
            f"total_api_calls={self.stats.api_calls:_}"
        )

        # Check whether total cost or instance cost limits have been exceeded
        if (
            self.args.total_cost_limit > 0
            and self.stats.total_cost >= self.args.total_cost_limit
        ):
            logger.warning(
                f"Cost {self.stats.total_cost:.2f} exceeds limit {self.args.total_cost_limit:.2f}"
            )
            raise CostLimitExceededError("Total cost limit exceeded")

        if (
            self.args.per_instance_cost_limit > 0
            and self.stats.instance_cost >= self.args.per_instance_cost_limit
        ):
            logger.warning(
                f"Cost {self.stats.instance_cost:.2f} exceeds limit {self.args.per_instance_cost_limit:.2f}"
            )
            raise CostLimitExceededError("Instance cost limit exceeded")
        return cost

    def query(self, history: list[dict[str, str]]) -> str:
        raise NotImplementedError("Use a subclass of BaseModel")


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
    }

    SHORTCUTS = {
        "gpt3": "gpt-3.5-turbo-1106",
        "gpt3-legacy": "gpt-3.5-turbo-16k-0613",
        "gpt4": "gpt-4-1106-preview",
        "gpt4-legacy": "gpt-4-0613",
        "gpt4-0125": "gpt-4-0125-preview",
        "gpt3-0125": "gpt-3.5-turbo-0125",
    }

    def __init__(self, args: ModelArguments, commands: list[Command]):
        super().__init__(args, commands)

        # Set OpenAI key
        cfg = config.Config(os.path.join(os.getcwd(), "keys.cfg"))
        if self.args.model_name.startswith("azure"):
            self.api_model = cfg["AZURE_OPENAI_DEPLOYMENT"]
            self.client = AzureOpenAI(api_key=cfg["AZURE_OPENAI_API_KEY"], azure_endpoint=cfg["AZURE_OPENAI_ENDPOINT"], api_version=cfg.get("AZURE_OPENAI_API_VERSION", "2024-02-01"))
        else:
            api_base_url: Optional[str] = cfg.get("OPENAI_API_BASE_URL", None)
            self.client = OpenAI(api_key=cfg["OPENAI_API_KEY"], base_url=api_base_url)

    def history_to_messages(
        self, history: list[dict[str, str]], is_demonstration: bool = False
    ) -> list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
            return '\n'.join([entry["content"] for entry in history])
        # Return history components with just role, content fields
        return [
            {k: v for k, v in entry.items() if k in ["role", "content"]}
            for entry in history
        ]

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
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
        except BadRequestError as e:
            raise CostLimitExceededError(f"Context window ({self.model_metadata['max_context']} tokens) exceeded")
        # Calculate + update costs, return response
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        self.update_stats(input_tokens, output_tokens)
        return response.choices[0].message.content

class AnthropicModel(BaseModel):
    MODELS = {
        "claude-instant": {
            "max_context": 100_000,
            "cost_per_input_token": 1.63e-06,
            "cost_per_output_token": 5.51e-06,
        },
        "claude-2": {
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
        "claude-3-haiku-20240307": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 2.5e-07,
            "cost_per_output_token": 1.25e-06,
        },
    }

    SHORTCUTS = {
        "claude": "claude-2",
        "claude-opus": "claude-3-opus-20240229",
        "claude-sonnet": "claude-3-sonnet-20240229",
        "claude-haiku": "claude-3-haiku-20240307",
    }

    def __init__(self, args: ModelArguments, commands: list[Command]):
        super().__init__(args, commands)

        # Set Anthropic key
        cfg = config.Config(os.path.join(os.getcwd(), "keys.cfg"))
        self.api = Anthropic(api_key=cfg["ANTHROPIC_API_KEY"])

    def history_to_messages(
        self, history: list[dict[str, str]], is_demonstration: bool = False
    ) -> list[dict[str, str]]:
        """
        Create `prompt` by filtering out all keys except for role/content per `history` turn
        Reference: https://docs.anthropic.com/claude/reference/complete_post
        """
        # Preserve behavior for older models
        if self.api_model in ["claude-instant", "claude-2"]:
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
            return '\n'.join([entry["content"] for entry in history])

        # Return history components with just role, content fields (no system message)
        messages = [
            {
                k: v for k, v in entry.items()
                if k in ["role", "content"]
            }
            for entry in history if entry["role"] != "system"
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

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, history: list[dict[str, str]]) -> str:
        """
        Query the Anthropic API with the given `history` and return the response.
        """
        # Preserve behavior for older models
        if self.api_model in ["claude-instant", "claude-2"]:
            # Perform Anthropic API call
            prompt = self.history_to_messages(history)
            input_tokens = self.api.count_tokens(prompt)
            completion = self.api.completions.create(
                model=self.api_model,
                prompt=prompt,
                max_tokens_to_sample=self.model_metadata["max_context"] - input_tokens,
                temperature=self.args.temperature,
                top_p=self.args.top_p,
            )
            # Calculate + update costs, return response
            response = completion.completion
            output_tokens = self.api.count_tokens(response)
            self.update_stats(input_tokens, output_tokens)
            return response

        # Get system message(s)
        system_message = "\n".join([
            entry["content"] for entry in history if entry["role"] == "system"
        ])
        messages = self.history_to_messages(history)
        # Perform Anthropic API call
        response = self.api.messages.create(
            messages=messages,
            max_tokens=self.model_metadata["max_tokens"],
            model=self.api_model,
            temperature=self.args.temperature,
            top_p=self.args.top_p,
            system=system_message,
        )

        # Calculate + update costs, return response
        self.update_stats(
            response.usage.input_tokens,
            response.usage.output_tokens
        )
        response = "\n".join([x.text for x in response.content])
        return response


class OllamaModel(BaseModel):
    MODELS = defaultdict(lambda: {
        "max_context": 128_000,
        "cost_per_input_token": 0,
        "cost_per_output_token": 0,
    })

    def __init__(self, args: ModelArguments, commands: list[Command]):
        super().__init__(args, commands)
        from ollama import Client
        self.client = Client(host=args.host_url)

    def history_to_messages(
        self, history: list[dict[str, str]], is_demonstration: bool = False
    ) -> list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
            return '\n'.join([entry["content"] for entry in history])
        # Return history components with just role, content fields
        return [
            {k: v for k, v in entry.items() if k in ["role", "content"]}
            for entry in history
        ]

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
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
            }
        )
        # Calculate + update costs, return response
        if "prompt_eval_count" in response:
            input_tokens = response["prompt_eval_count"]
        else:
            logger.warning(
                "Prompt eval count not found in response. Using 0. "
                "This might be because the prompt has been cached. "
                "See https://github.com/princeton-nlp/SWE-agent/issues/44 "
                "and https://github.com/ollama/ollama/issues/3427."
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

    def __init__(self, args: ModelArguments, commands: list[Command]):
        super().__init__(args, commands)

        # Set Together key
        cfg = config.Config(os.path.join(os.getcwd(), "keys.cfg"))
        together.api_key = cfg.TOGETHER_API_KEY

    def history_to_messages(
        self, history: list[dict[str, str]], is_demonstration: bool = False
    ) -> str:
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
        prompt = f"{prompt}\n<bot>:"
        return prompt

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, history: list[dict[str, str]]) -> str:
        """
        Query the Together API with the given `history` and return the response.
        """
        # Perform Together API call
        prompt = self.history_to_messages(history)
        completion = together.Complete.create(
            model=self.api_model,
            prompt=prompt,
            max_tokens=self.model_metadata["max_context"],
            stop="<human>",
            temperature=self.args.temperature,
            top_p=self.args.top_p,
        )
        # Calculate + update costs, return response
        response = completion["output"]["choices"][0]["text"].split("<human>")[0]
        input_tokens = completion["output"]["usage"]["prompt_tokens"]
        output_tokens = completion["output"]["usage"]["completion_tokens"]
        self.update_stats(input_tokens, output_tokens)
        return response


class HumanModel(BaseModel):
    MODELS = {"human": {}}

    def __init__(self, args: ModelArguments, commands: list[Command]):
        super().__init__(args, commands)

        # Determine which commands require multi-line input
        self.multi_line_command_endings = {
            command.name: command.end_name
            for command in commands
            if command.end_name is not None
        }

    def history_to_messages(
        self, history: list[dict[str, str]], is_demonstration: bool = False
    ) -> list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
            return '\n'.join([entry["content"] for entry in history])
        # Return history components with just role, content fields
        return [
            {k: v for k, v in entry.items() if k in ["role", "content"]}
            for entry in history
        ]

    def query(self, history: list[dict[str, str]], action_prompt: str = "> ") -> str:
        """
        Logic for handling user input to pass to SWEEnv
        """
        action = input(action_prompt)
        command_name = action.split()[0] if action else ""

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

    def __init__(self, args: ModelArguments, commands: list[Command]):
        super().__init__(args, commands)

        if self.args.replay_path == None or not os.path.exists(self.args.replay_path):
            raise ValueError(
                "--replay_path must point to a file that exists to run a replay policy"
            )

        self.replays = [
            list(json.loads(x).values())[0]
            for x in open(self.args.replay_path, "r").readlines()
        ]
        self.replay_idx = 0
        self.action_idx = 0

    def query(self, history: list[dict[str, str]]) -> str:
        """
        Logic for tracking which replay action to pass to SWEEnv
        """
        action = self.replays[self.replay_idx][self.action_idx]
        self.action_idx += 1

        # Assuming `submit` is always last action of replay trajectory
        if action == "submit":
            self.replay_idx += 1
            self.action_idx = 0

        return action


def get_model(args: ModelArguments, commands: Optional[list[Command]] = None):
    """
    Returns correct model object given arguments and commands
    """
    if commands is None:
        commands = []

    if args.model_name == "human":
        return HumanModel(args, commands)
    if args.model_name == "human_thought":
        return HumanThoughtModel(args, commands)
    if args.model_name == "replay":
        return ReplayModel(args, commands)
    elif args.model_name.startswith("gpt") or args.model_name.startswith("ft:gpt") or args.model_name.startswith("azure:gpt"):
        return OpenAIModel(args, commands)
    elif args.model_name.startswith("claude"):
        return AnthropicModel(args, commands)
    elif args.model_name.startswith("ollama"):
        return OllamaModel(args, commands)
    else:
        raise ValueError(f"Invalid model name: {args.model_name}")
