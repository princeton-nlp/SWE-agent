"""The reviewer implements a retry loop for the agent to retry
solving the issue and to select the best solution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class AbstractReviewer(ABC):
    """The reviewer checks a single solution and tries to predict
    if it successfully solves the issue.
    """

    @abstractmethod
    def accept(self, instance, submission) -> bool:
        """Returns True if the submission is believed to be correct"""


class AbstractBinaryReviewer(ABC):
    """The binary reviewer checks two solutions and tries to predict
    which one is better.
    """

    @abstractmethod
    def compare_submissions(self, instance, sub1, sub2) -> int:
        """Returns 0 if sub1 is better, 1 if sub2 is better"""


class AbstractReviewLoop(ABC):
    """The review loop controls how often the agent tries to solve
    the issue and how it selects the best solution.
    """

    @abstractmethod
    def retry(self) -> bool:
        """Returns True if the agent should retry solving the issue"""

    @abstractmethod
    def on_submit(self, submission) -> None:
        """Called when the agent submits a solution"""

    @abstractmethod
    def get_best(self):
        """Returns the best solution"""


@dataclass
class ReviewerConfig:
    """The configuration for the reviewer"""

    system_template: str
    instance_template: str


@dataclass
class BinaryReviewerConfig:
    """The configuration for the binary reviewer"""

    system_template: str
    instance_template: str
    #: Filter the following actions from the trajectory
    traj_filter: list[str] = field(default_factory=list)
    #: Format of the trajectory item
    traj_item_template: str = "Model: {response}\n\nObservation: {observation}"


@dataclass
class ReviewLoopConfig:
    """The configuration for the review loop"""

    max_samples: int = 2
    min_draws: int = 1
    max_accepted_draws: int = 0


class Reviewer(AbstractReviewer):
    def __init__(self, config: ReviewerConfig):
        self._config = config

    def format_messages(self, instance, submission):
        system_message = self._config.system_template
        user_message = self._config.instance_template.format(**instance, **submission)
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]


# todo: Couldn't I just replace the whole thing with Jinja templates?
class TrajectoryFormatter:
    def __init__(
        self,
        traj_filter: list[str] | None = None,
        traj_item_template: str = "Model: {response}\n\nObservation: {observation}",
    ):
        self._traj_filter = traj_filter or []
        self._traj_item_template = traj_item_template

    def _include_trajectory_item(self, item) -> bool:
        action = item["action"].strip()
        for f in self._traj_filter:
            if action.startswith(f):
                return False
        return True

    def _format_trajectory_item(self, response: str, observation: str, i: int, i_traj: int = 1) -> str:
        return self._traj_item_template.format(
            response=response,
            observation=observation,
            i=i,
            i_traj=i_traj,
        )

    def format_trajectory(self, trajectory: list[dict[str, str]], i_traj: int = 1) -> str:
        traj_messages = [
            (item["response"], item["observation"]) for item in trajectory if self._include_trajectory_item(item)
        ]
        return "\n\n".join(
            [
                self._format_trajectory_item(response, observation, i, i_traj=i_traj)
                for i, (response, observation) in enumerate(traj_messages)
            ]
        )


class BinaryReviewer(AbstractBinaryReviewer):
    def __init__(self, config: BinaryReviewerConfig):
        self._config = config
        self._traj_formatter = TrajectoryFormatter(
            traj_filter=config.traj_filter,
            traj_item_template=config.traj_item_template,
        )

    def format_messages(self, instance, sub1, sub2):
        system_message = self._config.system_template
        user_message = self._config.instance_template.format(
            **instance,
            **{f"{k}1": v for k, v in sub1.items()},
            **{f"{k}2": v for k, v in sub1.items()},
            traj1=self._traj_formatter.format_trajectory(sub1["traj"]["trajectory"], i_traj=1),
            traj2=self._traj_formatter.format_trajectory(sub2["traj"]["trajectory"], i_traj=2),
        )
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]


class ReviewLoop(AbstractReviewLoop):
    def __init__(
        self,
        instance: dict[str, Any],
        reviewer: AbstractReviewer,
        breviewer: AbstractBinaryReviewer,
        loop_config: ReviewLoopConfig,
    ):
        self._instance = instance
        self._reviewer = reviewer
        self._breviewer = breviewer
        self._loop_config = loop_config
        self._submissions = []
        #: Number of samples taken so far
        self._n_samples = 0
        #: Number of samples accepted by the reviewer so far
        self._n_accepted = 0

    def on_submit(self, submission) -> None:
        self._submissions.append(submission)
        self._n_samples += 1

    def retry(self) -> bool:
        if self._n_samples >= self._loop_config.max_samples:
            return False

        accept = self._reviewer.accept(self._instance, self._submissions[-1])
        if accept:
            self._n_accepted += 1

        if accept and self._n_samples >= self._loop_config.min_draws:
            return False

        if self._n_accepted >= self._loop_config.max_accepted_draws:
            return False

        return True


def review_loop_from_config(config) -> AbstractReviewLoop:
    # initializes the right classes all based on
    # the main config
    ...
