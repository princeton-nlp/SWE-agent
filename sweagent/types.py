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


TRAJECTORY_TYPE = list[TrajectoryStep]


class AgentInfo(TypedDict, total=False):
    # same as `APIStats` from models.py
    model_stats: dict[str, float]
    exit_status: str
    submission: str | None


@dataclass
class ReviewSubmission:
    """Information that's passed to the reviewer"""

    trajectory: TRAJECTORY_TYPE
    info: AgentInfo
