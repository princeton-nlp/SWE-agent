from __future__ import annotations

import pytest

from sweagent.agent.models import BaseModel
from sweagent.agent.reviewer import (
    BinaryReviewer,
    BinaryReviewerConfig,
    Reviewer,
    ReviewerConfig,
    ReviewLoopConfig,
    get_review_loop_from_config,
)


@pytest.fixture()
def dummy_reviewer_config() -> ReviewerConfig:
    return ReviewerConfig("system_template", "instance_template")


@pytest.fixture()
def dummy_binary_reviewer_config() -> BinaryReviewerConfig:
    return BinaryReviewerConfig("system_template", "instance_template")


@pytest.fixture()
def dummy_review_loop_config(dummy_reviewer_config, dummy_binary_reviewer_config) -> ReviewLoopConfig:
    return ReviewLoopConfig(dummy_reviewer_config, dummy_binary_reviewer_config)


class DeterminedModel(BaseModel):
    def __init__(self, replies: list[str]):
        self._replies = replies
        self._idx = 0

    def query(self, messages):
        reply = self._replies[self._idx]
        self._idx += 1
        return reply


def test_get_from_config(dummy_review_loop_config):
    get_review_loop_from_config(dummy_review_loop_config, instance={}, model=DeterminedModel([]))


def test_reviewer(dummy_reviewer_config):
    model = DeterminedModel(["success", "fail", "false", ""])
    reviewer = Reviewer(dummy_reviewer_config, model)
    instance = {}
    submission = {}
    assert reviewer.accept(instance, submission)
    assert not reviewer.accept(instance, submission)
    assert not reviewer.accept(instance, submission)
    assert not reviewer.accept(instance, submission)


def _get_fake_trajectory():
    return {
        "traj": {"trajectory": ""},
    }


def test_binary_reviewer(dummy_binary_reviewer_config):
    model = DeterminedModel(["first", "second", "false", ""])
    br = BinaryReviewer(dummy_binary_reviewer_config, model)
    instance = {}
    sub1 = _get_fake_trajectory()
    osub2 = _get_fake_trajectory()
    assert br.compare_submissions(instance, sub1, osub2) == 1
    assert br.compare_submissions(instance, sub1, osub2) == 2
    assert br.compare_submissions(instance, sub1, osub2) == 1
    assert br.compare_submissions(instance, sub1, osub2) == 1
