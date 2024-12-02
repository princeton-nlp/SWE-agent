"""This file has types/dataclass definitions that are used in the SWE agent
for exchanging data between different modules/functions/classes.
They oftentimes cannot be defined in the same file where they are used
because of circular dependencies.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel
from simple_parsing.helpers.serialization.serializable import FrozenSerializable
from typing_extensions import TypedDict


class StepOutput(BaseModel):
    thought: str = ""
    action: str = ""
    output: str = ""
    observation: str = ""
    execution_time: float = 0.0
    done: bool = False
    exit_status: str | None = None
    submission: str | None = None
    state: dict[str, str] = {}
    tool_calls: list[dict[str, str]] | None = None
    tool_call_ids: list[str] | None = None
    """State of the environment at the end of the step"""

    def to_template_format_dict(self) -> dict[str, str | int | float | bool | None]:
        """Used for formatting (error) prompt templates"""
        out = {}
        for k, v in self.model_dump().items():
            if k in ("tool_calls", "tool_call_ids", "state"):
                continue
            out[k] = v
        out |= self.state
        return out


class TrajectoryStep(TypedDict):
    action: str
    observation: str
    response: str
    state: dict[str, str]
    thought: str
    execution_time: float
    messages: list[dict[str, Any]]


# required fields go here
class _HistoryItem(TypedDict):
    role: str
    content: str
    message_type: Literal["thought", "action", "observation"]


# see _HistoryItem for required fields
class HistoryItem(_HistoryItem, total=False):
    agent: str
    is_demo: bool
    thought: str
    action: str | None
    tool_calls: list[dict[str, str]] | None
    tool_call_ids: list[str] | None
    tags: list[str]
    """HistoryProcessors can add these tags to enable special processing"""


History = list[HistoryItem]
Trajectory = list[TrajectoryStep]


# todo: Make this actually have the dataclasses instead of dict versions
class AgentInfo(TypedDict, total=False):
    # same as `APIStats` from models.py
    model_stats: dict[str, float]
    exit_status: str
    submission: str | None
    # same as `ReviewerResult`
    review: dict[str, Any]
    edited_files30: str
    edited_files50: str
    edited_files70: str
    # only if summarizer is used
    summarizer: dict
    swe_agent_hash: str
    swe_agent_version: str
    swe_rex_version: str
    swe_rex_hash: str


@dataclass
class ReviewSubmission:
    """Information that's passed to the reviewer"""

    #: Total trajectory (including several retries)
    trajectory: Trajectory
    #: Aggregate info dict (including several retries)
    info: AgentInfo

    def to_format_dict(self, *, suffix="") -> dict[str, Any]:
        """Return all the data that is used to format the
        messages. Trajectory is excluded because it needs special treatment.
        """
        out = {}
        info = copy.deepcopy(self.info)
        if not info.get("submission"):
            # Observed that not all exit_cost lead to autosubmission
            # so sometimes this might be missing.
            info["submission"] = ""
        for k, v in info.items():
            if isinstance(v, str):
                out[f"{k}{suffix}"] = v
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    out[f"{k}_{k2}{suffix}"] = v2
        return out


@dataclass(frozen=True)
class ReviewerResult(FrozenSerializable):
    accept: bool
    output: str
    messages: list[dict[str, str]]


@dataclass(frozen=True)
class BinaryReviewerResult(FrozenSerializable):
    choice: Literal[0, 1]
    output: str
    messages: list[dict[str, str]]


class AgentRunResult(BaseModel):
    info: AgentInfo
    trajectory: Trajectory
