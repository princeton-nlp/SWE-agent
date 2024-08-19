from __future__ import annotations

import textwrap
from abc import abstractmethod
from dataclasses import dataclass

from sweagent.environment.swe_env import SWEEnv


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

    _error_message = None

    @abstractmethod
    def __call__(self, observation, env: SWEEnv) -> str:
        """
        Abstract method for getting an observation and summarize it. 
        The returned value should be a summation of the given observation.
        """
        raise NotImplementedError

    @classmethod
    def get(cls, name):
        try:
            return cls._registry[name]()
        except KeyError:
            msg = f"Model output summarizer ({name}) not found."
            raise ValueError(msg)


# DEFINE NEW SUMMARIZE FUNCTIONS BELOW THIS LINE


class SimpleSummarizer(SummarizeFunction):
    """
    Saves the output of the command to a file and uses the open command to show the output. 
    """

    def __call__(self, observation, env: SWEEnv):
        return "0"
    

class Identity(SummarizeFunction):
    """
    This summarizer does not do any summation. It returns the environment observation as is.
    """

    def __call__(self, observation, env: SWEEnv):
        """
        This doesn't do any summarization. It just returns the environment observation.
        """
        return observation

