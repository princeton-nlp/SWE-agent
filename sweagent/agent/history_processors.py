from __future__ import annotations

import re
from abc import abstractmethod
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from sweagent.types import History, HistoryItem


class AbstractHistoryProcessor(Protocol):
    @abstractmethod
    def __call__(self, history: History) -> History:
        raise NotImplementedError


class DefaultHistoryProcessor(BaseModel):
    type: Literal["default"] = "default"
    """Do not change. Used for (de)serialization."""

    # pydantic config
    model_config = ConfigDict(extra="forbid")

    def __call__(self, history: History) -> History:
        return history


class LastNObservations(BaseModel):
    """Keep the last n observations."""

    n: int
    """Number of observations to keep."""

    always_remove_output_for_tags: set[str] = {"remove_output"}
    """Any observation with a `tags` field containing one of these strings will be elided,
    even if it is one of the last n observations.
    """

    always_keep_output_for_tags: set[str] = {"keep_output"}
    """Any observation with a `tags` field containing one of these strings will be kept,
    even if it is not one of the last n observations.
    """

    type: Literal["last_n_observations"] = "last_n_observations"
    """Do not change. Used for (de)serialization."""

    # pydantic config
    model_config = ConfigDict(extra="forbid")

    def __call__(self, history: History) -> History:
        if self.n <= 0:
            msg = "n must be a positive integer"
            raise ValueError(msg)
        new_history = list()
        observation_idxs = [
            idx
            for idx, entry in enumerate(history)
            if entry["message_type"] == "observation" and not entry.get("is_demo", False)
        ]
        omit_content_idxs = [idx for idx in observation_idxs[1 : -self.n]]
        for idx, entry in enumerate(history):
            tags = set(entry.get("tags", []))
            if ((idx not in omit_content_idxs) or (tags & self.always_keep_output_for_tags)) and not (
                tags & self.always_remove_output_for_tags
            ):
                new_history.append(entry)
            else:
                data = entry.copy()
                assert (
                    data["message_type"] == "observation"
                ), f"Expected observation for dropped entry, got: {data['message_type']}"
                data["content"] = f'Old environment output: ({len(entry["content"].splitlines())} lines omitted)'
                new_history.append(data)
        return new_history


class TagToolCallObservations(BaseModel):
    """Adds tags to history items for specific tool calls."""

    type: Literal["tag_tool_call_observations"] = "tag_tool_call_observations"
    """Do not change. Used for (de)serialization."""

    tags: set[str] = {"keep_output"}
    """Add the following tag to all observations matching the search criteria."""

    function_names: set[str] = set()
    """Only consider observations made by tools with these names."""

    # pydantic config
    model_config = ConfigDict(extra="forbid")

    def _add_tags(self, entry: HistoryItem) -> None:
        tags = set(entry.get("tags", []))
        tags.update(self.tags)
        entry["tags"] = list(tags)

    def _should_add_tags(self, entry: HistoryItem) -> bool:
        if entry["message_type"] != "action":
            return False
        function_calls = entry.get("tool_calls", [])
        if not function_calls:
            return False
        function_names = {call["function"]["name"] for call in function_calls}
        return bool(self.function_names & function_names)

    def __call__(self, history: History) -> History:
        for entry in history:
            if self._should_add_tags(entry):
                self._add_tags(entry)
        return history


class ClosedWindowHistoryProcessor(BaseModel):
    """For each value in history, keep track of which windows have been shown.
    We want to mark windows that should stay open (they're the last window for a particular file)
    Then we'll replace all other windows with a simple summary of the window (i.e. number of lines)
    """

    type: Literal["closed_window"] = "closed_window"
    """Do not change. Used for (de)serialization."""

    _pattern = re.compile(r"^(\d+)\:.*?(\n|$)", re.MULTILINE)
    _file_pattern = re.compile(r"\[File:\s+(.*)\s+\(\d+\s+lines\ total\)\]")

    # pydantic config
    model_config = ConfigDict(extra="forbid")

    def __call__(self, history):
        new_history = list()
        windows = set()
        for entry in reversed(history):
            data = entry.copy()
            if data["role"] != "user":
                new_history.append(entry)
                continue
            if data.get("is_demo", False):
                new_history.append(entry)
                continue
            matches = list(self._pattern.finditer(entry["content"]))
            if len(matches) >= 1:
                file_match = self._file_pattern.search(entry["content"])
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


HistoryProcessor = Annotated[
    DefaultHistoryProcessor | LastNObservations | ClosedWindowHistoryProcessor | TagToolCallObservations,
    Field(discriminator="type"),
]
