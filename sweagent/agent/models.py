from __future__ import annotations

import json
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import Annotated, Any, Literal

import litellm
import litellm.types.utils
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field, SecretStr
from swerex.exceptions import SweRexception
from tenacity import (
    Retrying,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from sweagent.tools.commands import Command
from sweagent.types import History, HistoryItem
from sweagent.utils.log import get_logger

logger = get_logger("swea-lm", emoji="🤖")


class RetryConfig(PydanticBaseModel):
    retries: int = 5
    """Number of retries"""
    min_wait: float = 1
    """Minimum wait time between retries (random exponential wait)"""
    max_wait: float = 15
    """Maximum wait time between retries (random exponential wait)"""


class GenericAPIModelConfig(PydanticBaseModel):
    name: str
    """Arguments configuring the model and its behavior."""
    per_instance_cost_limit: float = 3.0
    """Cost limit for every instance (task)"""
    total_cost_limit: float = 0.0
    """Total cost limit"""
    temperature: float = 1.0
    """Sampling temperature"""
    top_p: float = 1.0
    """Sampling top-p"""
    api_base: str | None = None
    api_version: str | None = None
    api_key: SecretStr | None = None
    stop: list[str] = []

    completion_kwargs: dict[str, Any] = {}
    """Additional kwargs to pass to `litellm.completion`"""

    convert_system_to_user: bool = False
    """Whether to convert system messages to user messages. This is useful for
    models that do not support system messages like o1.
    """

    retry: RetryConfig = RetryConfig()

    # pydantic
    model_config = ConfigDict(extra="forbid")

    @property
    def id(self) -> str:
        return f"{self.name}__t-{self.temperature:.2f}__p-{self.top_p:.2f}__c-{self.per_instance_cost_limit:.2f}"


class ReplayModelConfig(GenericAPIModelConfig):
    replay_path: Path
    """Path to replay file when using the replay model"""

    name: Literal["replay"] = "replay"
    """Do not change. Used for (de)serialization."""

    model_config = ConfigDict(extra="forbid")


class InstantEmptySubmitModelConfig(GenericAPIModelConfig):
    """Model that immediately submits an empty patch"""

    name: Literal["instant_empty_submit"] = "instant_empty_submit"
    """Do not change. Used for (de)serialization."""

    delay: float = 0.0
    """Delay before answering"""

    model_config = ConfigDict(extra="forbid")


class HumanModelConfig(GenericAPIModelConfig):
    name: Literal["human"] = "human"
    """Do not change. Used for (de)serialization."""

    model_config = ConfigDict(extra="forbid")


class HumanThoughtModelConfig(HumanModelConfig):
    name: Literal["human_thought"] = "human_thought"
    """Do not change. Used for (de)serialization."""

    model_config = ConfigDict(extra="forbid")


ModelConfig = Annotated[
    ReplayModelConfig
    | InstantEmptySubmitModelConfig
    | HumanModelConfig
    | HumanThoughtModelConfig
    | GenericAPIModelConfig,
    Field(union_mode="left_to_right"),
]


class GlobalStats(PydanticBaseModel):
    total_cost: float = 0
    """Cumulative cost for all instances so far"""


GLOBAL_STATS = GlobalStats()
GLOBAL_STATS_LOCK = Lock()


class InstanceStats(PydanticBaseModel):
    instance_cost: float = 0
    tokens_sent: int = 0
    tokens_received: int = 0
    api_calls: int = 0

    def __add__(self, other: InstanceStats) -> InstanceStats:
        return InstanceStats(
            **{field: getattr(self, field) + getattr(other, field) for field in self.model_fields.keys()},
        )


class ContextWindowExceededError(Exception):
    """Raised when the context window of a LM is exceeded"""


class CostLimitExceededError(Exception):
    """Raised when we exceed a cost limit"""


class InstanceCostLimitExceededError(CostLimitExceededError):
    """Raised when we exceed the cost limit set for one task instance"""


class TotalCostLimitExceededError(CostLimitExceededError):
    """Raised when we exceed the total cost limit"""


class AbstractModel(ABC):
    def __init__(self, config: PydanticBaseModel, commands: list[Command]):
        self.config: PydanticBaseModel
        self.stats: InstanceStats

    def reset_stats(self):
        self.stats = InstanceStats()

    @abstractmethod
    def query(self, history: History, action_prompt: str = "> ") -> str: ...


class HumanModel(AbstractModel):
    def __init__(self, config: HumanModelConfig, commands: list[Command]):
        self.config = config
        self.stats = InstanceStats()

        # Determine which commands require multi-line input
        self.multi_line_command_endings = {
            command.name: command.end_name for command in commands if command.end_name is not None
        }

    def query(self, history: History, action_prompt: str = "> ") -> str:
        """Logic for handling user input to pass to SWEEnv"""
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
    def query(self, history: History) -> str:
        """Logic for handling user input (both thought + action) to pass to SWEEnv"""
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


class ReplayModel(AbstractModel):
    def __init__(self, config: ReplayModelConfig, commands: list[Command]):
        self.config = config
        self.stats = InstanceStats()

        if not self.config.replay_path.exists():
            msg = f"Replay file {self.config.replay_path} not found"
            raise FileNotFoundError(msg)

        self._replays = [
            list(json.loads(x).values())[0] for x in Path(self.config.replay_path).read_text().splitlines(keepends=True)
        ]
        self._replay_idx = 0
        self._action_idx = 0

    def _next_replay(self) -> None:
        """Called after last action"""
        self._replay_idx += 1
        self._action_idx = 0

    def query(self, history: History) -> str:
        """Logic for tracking which replay action to pass to SWEEnv"""
        self.stats.api_calls += 1
        actions = self._replays[self._replay_idx]
        try:
            action = actions[self._action_idx]
        except IndexError:
            msg = (
                "This seems to be an incomplete trajectory. "
                "We reached the end of it, but `submit` was not called. "
                "Calling it now."
            )
            logger.warning(msg)
            action = "```\nsubmit\n```"

        self._action_idx += 1

        # Assuming `submit` is always last action of replay trajectory
        if action == "submit":
            self._next_replay()

        return action


class PredeterminedTestModel(AbstractModel):
    def __init__(self, outputs: list[str]):
        self._outputs = outputs
        self._idx = -1
        self.stats = InstanceStats()

    def query(self, *args, **kwargs) -> str:
        self._idx += 1
        output = self._outputs[self._idx]
        if output == "raise_runtime":
            raise SweRexception()
        elif output == "raise_cost":
            raise CostLimitExceededError()
        elif output == "raise_context":
            raise ContextWindowExceededError()
        return output


class InstantEmptySubmitTestModel(AbstractModel):
    def __init__(self, args: InstantEmptySubmitModelConfig, commands: list[Command]):
        """This model immediately submits. Useful for testing purposes"""
        self.config: InstantEmptySubmitModelConfig = args
        self.stats = InstanceStats()
        self._action_idx = 0

    def query(self, history: list[dict[str, str]]) -> str:
        time.sleep(random.uniform(0, self.config.delay))
        # Need to at least do _something_ to submit
        if self._action_idx == 0:
            self._action_idx = 1
            action = "DISCUSSION\nLet's reproduce the bug by creating a `reproduce.py` file.\n\n```\ncreate reproduce.py\n```\n"
        elif self._action_idx == 1:
            self._action_idx = 0
            action = "DISCUSSION\nThe task should be resolved, so let's submit the patch.\n\n```\nsubmit\n```\n"
        self.stats.api_calls += 1
        return action


class LiteLLMModel(AbstractModel):
    def __init__(self, args: ModelConfig, commands: list[Command]):
        self.args = args
        self.commands = commands
        self.stats = InstanceStats()

    def _update_stats(self, *, input_tokens: int, output_tokens: int, cost: float) -> None:
        with GLOBAL_STATS_LOCK:
            GLOBAL_STATS.total_cost += cost
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
            f"total_cost={GLOBAL_STATS.total_cost:.2f}, "
            f"total_api_calls={self.stats.api_calls:,}",
        )

        # Check whether total cost or instance cost limits have been exceeded
        if 0 < self.args.total_cost_limit <= GLOBAL_STATS.total_cost:
            logger.warning(f"Cost {GLOBAL_STATS.total_cost:.2f} exceeds limit {self.args.total_cost_limit:.2f}")
            msg = "Total cost limit exceeded"
            raise TotalCostLimitExceededError(msg)

        if 0 < self.args.per_instance_cost_limit <= self.stats.instance_cost:
            logger.warning(f"Cost {self.stats.instance_cost:.2f} exceeds limit {self.args.per_instance_cost_limit:.2f}")
            msg = "Instance cost limit exceeded"
            raise InstanceCostLimitExceededError(msg)

    def _query(self, messages: list[dict[str, str]]) -> str:
        input_tokens: int = litellm.utils.token_counter(messages=messages, model=self.args.name)
        max_input_tokens: int | None = litellm.model_cost.get(self.args.name, {}).get("max_input_tokens")
        if max_input_tokens is None:
            logger.warning(f"No max input tokens found for model {self.args.name!r}")
        elif input_tokens > max_input_tokens:
            msg = f"Input tokens {input_tokens} exceed max tokens {max_input_tokens}"
            raise ContextWindowExceededError(msg)
        extra_args = {}
        if self.args.api_base:
            # Not assigned a default value in litellm, so only pass this if it's set
            extra_args["api_base"] = self.args.api_base
        response: litellm.types.utils.ModelResponse = litellm.completion(  # type: ignore
            model=self.args.name,
            messages=messages,
            temperature=self.args.temperature,
            top_p=self.args.top_p,
            api_version=self.args.api_version,
            api_key=self.args.api_key.get_secret_value() if self.args.api_key else None,
            **self.args.completion_kwargs,
            **extra_args,
        )
        choices: litellm.types.utils.Choices = response.choices  # type: ignore
        output = choices[0].message.content
        cost = litellm.cost_calculator.completion_cost(response)
        output_tokens = litellm.utils.token_counter(text=output, model=self.args.name)
        self._update_stats(input_tokens=input_tokens, output_tokens=output_tokens, cost=cost)

        return output

    def query(self, history: History) -> str:
        for attempt in Retrying(
            stop=stop_after_attempt(self.args.retry.retries),
            wait=wait_random_exponential(min=self.args.retry.min_wait, max=self.args.retry.max_wait),
            reraise=True,
            retry=retry_if_not_exception_type(
                (
                    CostLimitExceededError,
                    RuntimeError,
                    litellm.exceptions.UnsupportedParamsError,
                    litellm.exceptions.NotFoundError,
                    litellm.exceptions.PermissionDeniedError,
                    litellm.exceptions.ContextWindowExceededError,
                    litellm.exceptions.ContentPolicyViolationError,
                    litellm.exceptions.APIError,
                )
            ),
        ):
            with attempt:
                messages = self._history_to_messages(history)
                result = self._query(messages)
        return result

    def _history_to_messages(
        self,
        history: History,
    ) -> list[dict[str, str]]:
        def get_role(history_item: HistoryItem) -> str:
            if history_item["role"] == "system":
                return "user" if self.args.convert_system_to_user else "system"
            return history_item["role"]

        return [{"role": get_role(history_item), "content": history_item["content"]} for history_item in history]


def get_model(args: ModelConfig, commands: list[Command] | None = None) -> AbstractModel:
    """Returns correct model object given arguments and commands"""
    if commands is None:
        commands = []

    if args.name == "human":
        assert isinstance(args, HumanModelConfig)
        return HumanModel(args, commands)
    if args.name == "human_thought":
        assert isinstance(args, HumanThoughtModelConfig)
        return HumanThoughtModel(args, commands)
    if args.name == "replay":
        assert isinstance(args, ReplayModelConfig)
        return ReplayModel(args, commands)
    elif args.name == "instant_empty_submit":
        assert isinstance(args, InstantEmptySubmitModelConfig)
        return InstantEmptySubmitTestModel(args, commands)
    assert isinstance(args, GenericAPIModelConfig)
    return LiteLLMModel(args, commands)
