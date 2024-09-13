from __future__ import annotations

import re
from abc import abstractmethod
from dataclasses import dataclass


class FormatError(Exception):
    pass


# ABSTRACT BASE CLASSES


class HistoryProcessorMeta(type):
    _registry = {}

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        if name != "HistoryProcessor":
            cls._registry[name] = new_cls
        return new_cls


@dataclass
class HistoryProcessor(metaclass=HistoryProcessorMeta):
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def __call__(self, history: list[str]) -> list[str]:
        raise NotImplementedError

    @classmethod
    def get(cls, name, *args, **kwargs):
        try:
            return cls._registry[name](*args, **kwargs)
        except KeyError:
            msg = f"Model output parser ({name}) not found."
            raise ValueError(msg)


# DEFINE NEW PARSING FUNCTIONS BELOW THIS LINE
class DefaultHistoryProcessor(HistoryProcessor):
    def __call__(self, history):
        return history

def may_compress(entry: dict):
    return entry["role"] == "user" and not entry.get("is_demo", False) and not entry.get("tdd", False)

def last_n_history(history, n):
    if n <= 0:
        msg = "n must be a positive integer"
        raise ValueError(msg)
    new_history = list()
    compressable_messages = len([entry for entry in history if may_compress(entry)])
    user_msg_idx = 0
    for entry in history:
        if not may_compress(entry):
            new_history.append(entry)
            continue
        else:
            user_msg_idx += 1
        if user_msg_idx == 1 or user_msg_idx in range(compressable_messages - n + 1, compressable_messages + 1):
            new_history.append(entry)
        else:
            data = entry.copy()
            from sweagent.agent.models import compress_history_entry
            compress_history_entry(data)
            new_history.append(data)
    return new_history


class LastNObservations(HistoryProcessor):
    def __init__(self, n):
        self.n = n

    def __call__(self, history):
        return last_n_history(history, self.n)


class Last2Observations(HistoryProcessor):
    def __call__(self, history):
        return last_n_history(history, 2)


class Last5Observations(HistoryProcessor):
    def __call__(self, history):
        return last_n_history(history, 5)


class ClosedWindowHistoryProcessor(HistoryProcessor):
    pattern = re.compile(r"^(\d+)\:.*?(\n|$)", re.MULTILINE)
    file_pattern = re.compile(r"\[File:\s+(.*)\s+\(\d+\s+lines\ total\)\]")

    def __call__(self, history):
        new_history = list()
        # For each value in history, keep track of which windows have been shown.
        # We want to mark windows that should stay open (they're the last window for a particular file)
        # Then we'll replace all other windows with a simple summary of the window (i.e. number of lines)
        windows = set()
        for entry in reversed(history):
            data = entry.copy()
            if not may_compress(entry):
                new_history.append(entry)
                continue
            matches = list(self.pattern.finditer(entry["content"]))
            if len(matches) >= 1:
                file_match = self.file_pattern.search(entry["content"])
                if file_match:
                    file = file_match.group(1)
                else:
                    continue
                if file in windows:
                    start = matches[0].start()
                    end = matches[-1].end()
                    data["content"] = (
                        entry["content"][:start]
                        + f"Outdated window with {len(matches)} lines omitted...\n"
                        + entry["content"][end:]
                    )
                windows.add(file)
            new_history.append(data)
        return list(reversed(new_history))
