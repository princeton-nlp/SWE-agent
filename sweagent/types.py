"""This file has types/dataclass definitions that are used in the SWE agent
for exchanging data between different modules/functions/classes.
They oftentimes cannot be defined in the same file where they are used
because of circular dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


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


class AgentInfo(TypedDict, total=False):
    # same as `APIStats` from models.py
    model_stats: dict[str, float]
    exit_status: str
    submission: str | None


@dataclass
class ReviewSubmission:
    """Information that's passed to the reviewer"""

    #: Total trajectory (including several retries)
    trajectory: Trajectory
    #: Aggregate info dict (including several retries)
    info: AgentInfo
