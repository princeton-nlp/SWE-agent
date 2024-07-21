"""The reviewer implements a retry loop for the agent to retry
solving the issue and to select the best solution.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from simple_parsing.helpers.serialization.serializable import FrozenSerializable

from sweagent.agent.models import APIStats, BaseModel
from sweagent.types import BinaryReviewerResult, ReviewerResult, ReviewSubmission, Trajectory, TrajectoryStep
from sweagent.utils.log import get_logger

INSTANCE_TYPE = dict[str, Any]

logger = get_logger("reviewer")

# --- INTERFACES ---


class AbstractReviewer(ABC):
    """The reviewer checks a single solution and tries to predict
    if it successfully solves the issue.
    """

    @abstractmethod
    def review(self, instance: INSTANCE_TYPE, submission: ReviewSubmission) -> ReviewerResult:
        """Returns True if the submission is believed to be correct"""


class AbstractBinaryReviewer(ABC):
    """The binary reviewer checks two solutions and tries to predict
    which one is better.
    """

    @abstractmethod
    def compare_submissions(
        self,
        instance: INSTANCE_TYPE,
        sub1: ReviewSubmission,
        sub2: ReviewSubmission,
        rev1: ReviewerResult,
        rev2: ReviewerResult,
    ) -> BinaryReviewerResult:
        """Returns 0 if sub1 is better, 1 if sub2 is better"""


class AbstractGraveToCradle(ABC):
    """Forward messages from past attempts to the next one"""

    @abstractmethod
    def get_forwarded_vars(
        self,
        submissions: list[ReviewSubmission],
        reviews: list[ReviewerResult],
        breviews: list[tuple[int, int, BinaryReviewerResult]],
    ) -> dict[str, Any]:
        """Get the variables that should be forwarded to the next iteration.

        Note: Must return a dictionary with the correct keys even when called
        with empty lists. This is because else we cannot use the variables in the template
        when we call for the first attempt.

        Returns:
            A dictionary of variables that should be forwarded to the next iteration.
        """


class AbstractReviewLoop(ABC):
    """The review loop controls how often the agent tries to solve
    the issue and how it selects the best solution.
    """

    @abstractmethod
    def retry(self) -> bool:
        """Returns True if the agent should retry solving the issue"""

    @abstractmethod
    def on_submit(self, submission: ReviewSubmission) -> None:
        """Called when the agent submits a solution"""

    @abstractmethod
    def get_best(self) -> int:
        """Returns the best solution"""

    @property
    @abstractmethod
    def model_stats(self) -> APIStats:
        """Returns the API stats of the model (if any)"""

    @property
    @abstractmethod
    def reviews(self) -> list[ReviewerResult]: ...

    @property
    @abstractmethod
    def comparisons(self) -> list[tuple[int, int, BinaryReviewerResult]]:
        """Get information about comparisons

        Returns:
            A list of tuples, where each tuple contains the indices of the
            compared submissions and the result of the comparison.
        """

    def get_forwarded_vars(self) -> dict[str, Any]:
        """Get the variables that should be forwarded to the next iteration.

        Returns:
            A dictionary of variables that should be forwarded to the next iteration.
        """
        return {}


# --- CONFIGS ---


@dataclass(frozen=True)
class ReviewerConfig(FrozenSerializable):
    """The configuration for the reviewer"""

    system_template: str
    instance_template: str
    #: If a submission autosubmits because of total cost, it will be automatically
    #: rejected
    reject_exit_cost: bool = True
    #: Filter the following actions from the trajectory
    traj_filter: list[str] = field(default_factory=list)
    #: Filter outputs from the following actions from the trajectory
    traj_output_filter: list[str] = field(default_factory=list)
    #: Format of the trajectory item
    traj_item_template: str = "Model: {response}\n\nObservation: {observation}"
    filter_failed_edits: bool = False


@dataclass(frozen=True)
class BinaryReviewerConfig(FrozenSerializable):
    """The configuration for the binary reviewer"""

    system_template: str
    instance_template: str
    #: Filter the following actions from the trajectory
    traj_filter: list[str] = field(default_factory=list)
    #: Format of the trajectory item
    traj_item_template: str = "Model: {response}\n\nObservation: {observation}"
    traj_output_filter: list[str] = field(default_factory=list)
    traj_filter_failed_edits: bool = False
    traj_only_show_last_n_output: int = 0


@dataclass(frozen=True)
class GTCConfig(FrozenSerializable):
    """The configuration for the GraveToCradle"""


@dataclass(frozen=True)
class ReviewLoopConfig(FrozenSerializable):
    """The configuration for the review loop"""

    review_loop_classname: str
    reviewer_config: ReviewerConfig | None = None
    binary_reviewer_config: BinaryReviewerConfig | None = None
    gtc_config: GTCConfig | None = None
    reviewer_classname: str | None = None
    binary_reviewer_classname: str | None = None
    gtc_classname: str = ""
    #: Maximal number of attempts
    max_samples: int = 2
    #: Minimal number of attempts.
    min_draws: int = 1
    #: For use together with a `min_draws > 1`. Even if we have
    #: not reached the `min_draws`, we will stop if we have accepted
    #: `max_accepted_draws` submissions.
    max_accepted_draws: int = 0

    def validate(self):
        """Checks config. Raises `ValueError` in case of misconfiguration"""
        if self.min_draws < 1:
            msg = "`min_draws` must be at least 1"
            raise ValueError(msg)
        if self.max_samples < 1:
            msg = "`max_samples` must be at least 1"
            raise ValueError(msg)
        if self.max_samples < self.min_draws:
            msg = "`max_samples` must be greater than or equal to `min_draws`"
            raise ValueError(msg)
        if self.max_accepted_draws > self.min_draws:
            msg = "`max_accepted_draws` must be less than or equal to `min_draws`, else it has no effect"
            raise ValueError(msg)

    def __post_init__(self):
        self.validate()


# --- IMPLEMENTATIONS ---


class Reviewer(AbstractReviewer):
    LOG_PREFIX = "🧑‍⚖️ Reviewer: "

    def __init__(self, config: ReviewerConfig, model: BaseModel):
        self._config = config
        self._model = model
        self._traj_formatter = TrajectoryFormatter(
            traj_filter=config.traj_filter,
            traj_item_template=config.traj_item_template,
            traj_output_filter=config.traj_output_filter,
            filter_failed_edits=config.filter_failed_edits,
        )

    def format_messages(self, instance: INSTANCE_TYPE, submission: ReviewSubmission):
        system_message = self._config.system_template
        logger.debug(f"{self.LOG_PREFIX}MODEL INPUT (system)\n{system_message}")
        user_message = self._config.instance_template.format(
            **instance,
            **submission.to_format_dict(),
            traj=self._traj_formatter.format_trajectory(submission.trajectory),
        )
        logger.debug(f"{self.LOG_PREFIX}MODEL INPUT (user)\n{user_message}")
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    def interpret(self, response: str) -> bool:
        last_line = response.strip().split("\n")[-1].strip()
        if "success" in last_line.lower():
            return True
        elif "fail" in last_line.lower():
            return False
        logger.warning("Could not interpret response: %s, will reject submission.", response)
        return False

    def review(self, instance: dict[str, Any], submission: ReviewSubmission) -> ReviewerResult:
        exit_status = submission.info.get("exit_status")
        messages = []
        if not exit_status:
            answer = "No exit status in submission, will reject."
            accept = False
        elif self._config.reject_exit_cost and "exit_cost" in exit_status:
            answer = "Submission rejected because of exit cost."
            accept = False
        else:
            messages = self.format_messages(instance, submission)
            answer = self._model.query(messages)
            accept = self.interpret(answer)
        accept_emoji = "✅" if accept else "❌"
        logger.info(f"{self.LOG_PREFIX}{accept_emoji}\n{answer}")
        return ReviewerResult(accept, answer, messages=messages)


# todo: Couldn't I just replace the whole thing with Jinja templates?
class TrajectoryFormatter:
    def __init__(
        self,
        *,
        traj_filter: list[str] | None = None,
        traj_output_filter: list[str] | None = None,
        traj_item_template: str = "Model: {response}\n\nObservation: {observation}",
        filter_failed_edits: bool = False,
        only_show_last_n_output: int = 0,
    ):
        """Formats trajectories for the use in prompts"""
        self._traj_filter = traj_filter or []
        self._traj_output_filter = traj_output_filter or []
        self._traj_item_template = traj_item_template
        self._filter_failed_edits = filter_failed_edits
        self._only_show_last_n_output = only_show_last_n_output

    def _include_step(self, item: TrajectoryStep) -> bool:
        action = item["action"].strip()
        for f in self._traj_filter:
            if action.startswith(f):
                return False
        if self._filter_failed_edits and "Your proposed edit has introduced new syntax error(s)" in item["observation"]:
            return False
        return True

    def _include_step_output(self, item: TrajectoryStep, i_step: int, n_steps: int) -> bool:
        if self._only_show_last_n_output > 0 and i_step < n_steps - self._only_show_last_n_output:
            return False
        action = item["action"].strip()
        for f in self._traj_output_filter:
            if action.startswith(f):
                return False
        return True

    def _format_trajectory_step(self, step: TrajectoryStep, i_step: int, *, n_steps: int, i_traj: int = 1) -> str:
        step = copy.deepcopy(step)
        if not self._include_step_output(step, i_step, n_steps=n_steps):
            step["observation"] = "[Output omitted]"
        return self._traj_item_template.format(
            **step,
            i_step=i_step,
            i_traj=i_traj,
        )

    def format_trajectory(self, trajectory: Trajectory, i_traj: int = 1) -> str:
        traj_messages = [step for step in trajectory if self._include_step(step)]
        return "\n\n".join(
            [
                self._format_trajectory_step(step, i_step, i_traj=i_traj, n_steps=len(traj_messages))
                for i_step, step in enumerate(traj_messages)
            ]
        )


class BinaryReviewer(AbstractBinaryReviewer):
    LOG_PREFIX = "⚖️ Binary Reviewer: "

    def __init__(self, config: BinaryReviewerConfig, model: BaseModel):
        self._config = config
        self._model = model
        self._traj_formatter = TrajectoryFormatter(
            traj_filter=config.traj_filter,
            traj_item_template=config.traj_item_template,
            traj_output_filter=config.traj_output_filter,
            filter_failed_edits=config.traj_filter_failed_edits,
            only_show_last_n_output=config.traj_only_show_last_n_output,
        )

    def format_messages(self, instance: INSTANCE_TYPE, sub1: ReviewSubmission, sub2: ReviewSubmission):
        system_message = self._config.system_template
        logger.debug(f"{self.LOG_PREFIX}MODEL INPUT (system)\n{system_message}")
        user_message = self._config.instance_template.format(
            **instance,
            **sub1.to_format_dict(suffix="1"),
            **sub2.to_format_dict(suffix="2"),
            traj1=self._traj_formatter.format_trajectory(sub1.trajectory, i_traj=1),
            traj2=self._traj_formatter.format_trajectory(sub2.trajectory, i_traj=2),
        )
        logger.debug(f"{self.LOG_PREFIX}MODEL INPUT (user)\n{user_message}")
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    def interpret(self, response: str) -> Literal[0, 1]:
        """Interpret response from LM. Note: 1-based indexing"""
        last_line = response.strip().split("\n")[-1].strip()
        if "first" in last_line.lower():
            return 0
        elif "second" in last_line.lower():
            return 1
        logger.warning("Could not interpret response: %s, will choose first submission.", response)
        return 0

    def compare_submissions(
        self,
        instance: INSTANCE_TYPE,
        sub1: ReviewSubmission,
        sub2: ReviewSubmission,
        rev1: ReviewerResult,
        rev2: ReviewerResult,
    ) -> BinaryReviewerResult:
        messages = self.format_messages(instance, sub1, sub2)
        answer = self._model.query(messages)
        idx = self.interpret(answer)
        # Use words because else confusion with 0-based vs 1-based indices
        choice_emoji = "first" if idx == 0 else "second"
        logger.info(f"{self.LOG_PREFIX}{choice_emoji}\n{answer}")
        return BinaryReviewerResult(idx, output=answer, messages=messages)


class GraveToCradle(AbstractGraveToCradle):
    def __init__(self, config: GTCConfig, model: BaseModel):
        self._config = config
        self._model = model

    def get_forwarded_vars(
        self,
        submissions: list[ReviewSubmission],
        reviews: list[ReviewerResult],
        breviews: list[tuple[int, int, BinaryReviewerResult]],
    ) -> dict[str, Any]:
        assert len(submissions) == len(reviews)
        failed_idxs = [i for i, r in enumerate(reviews) if not r.accept]
        if not failed_idxs:
            return {"failed_verdicts_with_submissions": ""}
        msg_lines = ["The following previous submissions were deemed to be incorrect:"]
        for i, idx in enumerate(failed_idxs):
            info = submissions[idx].info
            if not info.get("submission"):
                continue
            submission = info["submission"]
            review = reviews[idx].output
            msg_lines.append(f"Submission {i+1}:\n\n{submission}\n\nReview {i+1}:\n\n{review}")
        msg = "\n\n".join(msg_lines)
        return {"failed_verdicts_with_submissions": msg}


class ReviewLoop(AbstractReviewLoop):
    LOG_PREFIX = "🔄 Review Loop: "

    def __init__(
        self,
        loop_config: ReviewLoopConfig,
        instance: INSTANCE_TYPE,
        model: BaseModel,
    ):
        self._model = model
        self._instance = instance
        self._reviewer: AbstractReviewer = globals()[loop_config.reviewer_classname](loop_config.reviewer_config, model)
        if loop_config.binary_reviewer_classname is not None:
            self._breviewer: AbstractBinaryReviewer | None = globals()[loop_config.binary_reviewer_classname](
                loop_config.binary_reviewer_config, model
            )
        else:
            self._breviewer = None
        self._gtc: AbstractGraveToCradle | None = None
        if loop_config.gtc_classname:
            self._gtc = globals()[loop_config.gtc_classname](loop_config.gtc_config, model)
        self._loop_config = loop_config
        # Note: These are "cumulative" submissions, i.e., they include all retries
        # up to that point.
        self._submissions: list[ReviewSubmission] = []
        self._reviews: list[ReviewerResult] = []
        self._comparisons: list[tuple[int, int, BinaryReviewerResult]] = []
        # Once we have k submissions, there will always be one voted at the
        # top through k calls to the binary reviewer. Here, we store the
        # corresponding index
        self._best_idx: int = 0

    @property
    def reviews(self) -> list[ReviewerResult]:
        return self._reviews

    @property
    def comparisons(self) -> list[tuple[int, int, BinaryReviewerResult]]:
        return self._comparisons

    @property
    def _n_samples(self) -> int:
        return len(self._submissions)

    @property
    def _n_accepted(self) -> int:
        return sum([r.accept for r in self._reviews])

    @property
    def model_stats(self) -> APIStats:
        return self._model.stats

    def on_submit(self, submission: ReviewSubmission) -> None:
        self._submissions.append(submission)
        self._review()
        self._compare()

    def _review(self) -> bool:
        review = self._reviewer.review(self._instance, self._submissions[-1])
        self._reviews.append(review)
        return review.accept

    def _compare(self) -> None:
        if self._breviewer is None:
            self._best_idx = self._n_samples - 1
            return
        if self._n_samples < 2:
            return
        if self._reviews[self._best_idx].accept and not self._reviews[-1].accept:
            # Require that the best submission is accepted, so don't
            # even need to compare here
            return
        if not self._reviews[self._best_idx].accept and self._reviews[-1].accept:
            # If the best submission is not accepted, but the last one is,
            # then the last one is the new best
            self._best_idx = self._n_samples - 1
            return
        sub1 = self._submissions[self._best_idx]
        sub2 = self._submissions[-1]
        rev1 = self._reviews[self._best_idx]
        rev2 = self._reviews[-1]
        cresult = self._breviewer.compare_submissions(self._instance, sub1, sub2, rev1, rev2)
        self._comparisons.append((self._n_samples - 2, self._n_samples - 1, cresult))
        assert cresult.choice in [0, 1]
        # this was a comparison between the current best and the last one
        self._best_idx = [self._best_idx, self._n_samples - 1][cresult.choice]

    def retry(self) -> bool:
        stat_str = f"n_samples={self._n_samples}, n_accepted={self._n_accepted}"
        # n_samples is 1-based
        if self._n_samples >= self._loop_config.max_samples:
            # We've exceeded our budget. Returning best solution no matter what.
            logger.info(f"{self.LOG_PREFIX}Exiting retry loop ({stat_str}): `max_samples` reached")
            return False

        if self._n_accepted and self._n_samples >= self._loop_config.min_draws:
            # We have an accepted submission and have reached the minimum number of draws
            logger.info(
                f"{self.LOG_PREFIX}Existing retry loop ({stat_str}): `min_draws` reached and last submission was accepted"
            )
            return False

        if self._n_accepted >= self._loop_config.max_accepted_draws > 0:
            # We have reached more than the required number of accepted submissions.
            # Exiting even if we haven't reached the minimum number of draws.
            logger.info(f"{self.LOG_PREFIX}Exiting retry loop ({stat_str}): `max_accepted_draws` reached")
            return False

        return True

    def get_best(self) -> int:
        if self._breviewer is not None:
            assert len(self._reviews) == len(self._submissions)
        return self._best_idx

    def get_forwarded_vars(self) -> dict[str, Any]:
        if self._gtc is None:
            return {}
        return self._gtc.get_forwarded_vars(self._submissions, self._reviews, self._comparisons)


def get_review_loop_from_config(
    config: ReviewLoopConfig | None, instance: INSTANCE_TYPE, model: BaseModel
) -> AbstractReviewLoop | None:
    if config is None:
        logger.debug("Running without review loop")
        return None
    return globals()[config.review_loop_classname](config, instance, model)
