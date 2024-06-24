"""This file has types/dataclass definitions that are used in the SWE agent
for exchanging data between different modules/functions/classes.
They oftentimes cannot be defined in the same file where they are used
because of circular dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from simple_parsing.helpers.serialization.serializable import FrozenSerializable


class TrajectoryStep(TypedDict):
    action: str
    observation: str
    response: str
    state: str | None
    thought: str


class _HistoryItem(TypedDict):
    role: str


class HistoryItem(_HistoryItem, total=False):
    content: str | None
    agent: str
    is_demo: bool
    thought: str
    action: str | None


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
        for k, v in self.info.items():
            if isinstance(v, str):
                out[f"{k}{suffix}"] = v
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
