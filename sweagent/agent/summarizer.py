from __future__ import annotations

import shlex
import textwrap
from abc import abstractmethod
from dataclasses import dataclass

from sweagent.environment.swe_env import SWEEnv
from sweagent.utils.log import get_logger


# ABSTRACT BASE CLASSES


class SummarizeFunctionMeta(type):
    """
    Registry maps all inherited classes to their names.
    """

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

    def __init__(self, window_length: int):
        self._window_length = window_length
        self.logger = get_logger("summarizer")

    @abstractmethod
    def __call__(self, input: str, observation, env: SWEEnv) -> str:
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

    def __call__(self, input: str, observation: str, env: SWEEnv) -> str:
        try:
            if any(input.startswith(s) for s in self.block_list_input) or len(observation.splitlines()) <= self._window_length:
                return observation
            self.logger.debug(f"Summarizing current observation for input {input}")
            command_file_name = "/output/" + input.replace(" ", "_").replace("/", "__")
            observation = f"COMMAND OUTPUT EXCEEDED WINDOW, SAVED COMMAND TO A FILE {command_file_name} AND OPENED THE FILE AT LINE 0.\n\n\n{observation}"
            env.communicate("mkdir -p /output")
            env.communicate(f"printf {shlex.quote(observation)} > {command_file_name}")
            return env.communicate(f"open {command_file_name}")
        except Exception as e:
            self.logger.warning(f"Unhandled exception occured when trying to summarize observation for input {input}: {e}")
            return observation
    

class Identity(SummarizeFunction):
    """
    This summarizer does not do any summation. It returns the environment observation as is.
    """

    def __call__(self, input: str, observation: str, env: SWEEnv) -> str:
        """
        This doesn't do any summarization. It just returns the environment observation.
        """
        return observation

