from __future__ import annotations

import shlex
import textwrap
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from sweagent.agent.models import APIStats, BaseModel, ContextWindowExceededError
from sweagent.environment.swe_env import SWEEnv
from sweagent.utils.log import get_logger


# ABSTRACT BASE CLASSES


class SummarizeFunctionMeta(type):
    """
    Registry maps all inherited classes to their names.
    """

    _warning_message = None

    _registry = {}

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        if name != "SummarizeFunction":
            cls._registry[name] = new_cls
        return new_cls


@dataclass
class SummarizeFunction(metaclass=SummarizeFunctionMeta):
    """
    Abstract class for summarizing functions.
    We use get to generate the right summarizer based on the name of the summarizer.
    """

    def __init__(self, window_length: int | None):
        self._window_length = window_length
        self.logger = get_logger("summarizer")

    def setup(self, instance_args: dict[str, Any], config):
        """
        Additional setup function for the summarizer.
        """
        pass

    @abstractmethod
    def __call__(self, input: str, observation, env: SWEEnv, model: type[BaseModel]) -> tuple[str, APIStats]:
        """
        Abstract method for getting an observation and summarize it. 
        The returned value should be a summation of the given observation.
        """
        raise NotImplementedError

    @classmethod
    def get(cls, name: str, window_length: int):
        try:
            return cls._registry[name](window_length)
        except KeyError:
            msg = f"Model output summarizer ({name}) not found."
            raise ValueError(msg)


# DEFINE NEW SUMMARIZE FUNCTIONS BELOW THIS LINE


class SimpleSummarizer(SummarizeFunction):
    """
    Saves the output of the command to a file and uses the open command to show the output. 
    """

    _warning_message = """\
        Warning: Command output exceeded window, saved command to a file {command_file_name} and opened the file at line 1.
        

    """

    block_list_input = [
        "create",
        "open",
        "edit",
        "scroll_up",
        "scroll_down",
        "goto",
        "search_file",
        "search_dir",
    ]

    def __call__(self, input: str, observation: str, env: SWEEnv, model: type[BaseModel]) -> tuple[str, APIStats]:
        try:
            if any(input.startswith(s) for s in self.block_list_input) or len(observation.splitlines()) <= self._window_length:
                return observation, APIStats()
            self.logger.debug(f"Summarizing current observation for input {input}")
            command_file_name = "/output/" + input.replace(" ", "_").replace("/", "__")
            env.communicate("mkdir -p /output")
            env.communicate(f"printf {shlex.quote(observation)} > {command_file_name}")
            return textwrap.dedent(self._warning_message.format(command_file_name=command_file_name)) + env.communicate(f"open {command_file_name}"), APIStats()
        except Exception as e:
            self.logger.warning(f"Unhandled exception occured when trying to summarize observation for input {input}: {e}")
            return observation, APIStats()
    

class Identity(SummarizeFunction):
    """
    This summarizer does not do any summation. It returns the environment observation as is.
    """

    def __call__(self, input: str, observation: str, env: SWEEnv, model: type[BaseModel]) -> tuple[str, APIStats]:
        """
        This doesn't do any summarization. It just returns the environment observation.
        """
        return observation, APIStats()


class LMSummarizer(SummarizeFunction):
    _warning_message = """\
    Warning: Command output exceeded window size, saved command to a file {command_file_name} and summarized the command output for you.
    If you still want to view the output of the command, use the following command `open {command_file_name}`.
    
    
    SUMMARY:
    """

    _warning_message_summarization_failed = """\
    Warning: Command output exceeded window size, saved command to a file {command_file_name}.
    If you still want to view the output of the command, use the following command `open {command_file_name}`.
    """

    block_list_input = [
        "create",
        "open",
        "edit",
        "scroll_up",
        "scroll_down",
        "goto",
        "search_file",
        "search_dir",
    ]
    
    def __init__(self, window_length: int):
        super().__init__(window_length)
        self.history = []

    def setup(self, instance_args: dict[str, Any], config):
        self.name = "ctf_summarizer"
        system_msg = config.summarizer_system_template.format(**config.__dict__)
        self.history.append({"role": "system", "content": system_msg, "agent": self.name})
        self.logger.info(f"SYSTEM ({self.name})\n{system_msg}")
        self.instance_template = config.summarizer_instance_template
        self.instance_args = instance_args
        self.system_args = config.__dict__

    @staticmethod 
    def _slugify_action(action: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in action)[:30]

    def __call__(self, input: str, observation: str, env: SWEEnv, model: type[BaseModel]) -> tuple[str, APIStats]:
        try:
            if any(input.startswith(s) for s in self.block_list_input) or len(observation.splitlines()) <= self._window_length:
                return observation, APIStats()
            self.logger.debug(f"Summarizing current observation for input {input}")
            command_file_name = "/output/" + self._slugify_action(input)
            env.communicate("mkdir -p /output")
            env.communicate(f"printf {shlex.quote(observation)} > {command_file_name}")
            self.history.append({"role": "user", "content": self.instance_template.format(**self.instance_args, **self.system_args, command=input, observation=observation), "agent": self.name})
            try:
                response = model.query(history=self.history)
                stats = model.stats
                model.reset_stats(APIStats())
                self.history.pop()
                return textwrap.dedent(self._warning_message.format(command_file_name=command_file_name)) + response, stats
            except ContextWindowExceededError:
                return textwrap.dedent(self._warning_message_summarization_failed.format(command_file_name=command_file_name)), APIStats()
        except Exception as e:
            self.logger.warning(f"Unhandled exception occured when trying to summarize observation for input {input}: {e}")
            return observation, APIStats()
        
