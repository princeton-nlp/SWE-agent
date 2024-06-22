from __future__ import annotations

import pytest

from run import ActionsArguments, Main, ScriptArguments
from sweagent import CONFIG_DIR
from sweagent.agent.agents import Agent, AgentArguments, AgentHook
from sweagent.agent.models import BaseModel, ModelArguments
from sweagent.agent.reviewer import (
    BinaryReviewer,
    BinaryReviewerConfig,
    Reviewer,
    ReviewerConfig,
    ReviewLoop,
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
    return ReviewLoopConfig(
        "ReviewLoop",
        dummy_reviewer_config,
        dummy_binary_reviewer_config,
    )


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
    assert reviewer.review(instance, submission).accept
    assert not reviewer.review(instance, submission).accept
    assert not reviewer.review(instance, submission).accept
    assert not reviewer.review(instance, submission).accept


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
    assert br.compare_submissions(instance, sub1, osub2).choice == 0
    assert br.compare_submissions(instance, sub1, osub2).choice == 1
    assert br.compare_submissions(instance, sub1, osub2).choice == 0
    assert br.compare_submissions(instance, sub1, osub2).choice == 0


def test_loop_comparison(dummy_reviewer_config, dummy_binary_reviewer_config):
    rmodel = DeterminedModel(["success", "fail", "success", "fail"])
    # Only have one comparison: The two successes
    bmodel = DeterminedModel(["second"])
    lconfig = ReviewLoopConfig(
        "ReviewLoop",
        dummy_reviewer_config,
        dummy_binary_reviewer_config,
        max_samples=100,
        min_draws=100,
        max_accepted_draws=2,
    )
    loop = ReviewLoop(lconfig, instance={}, model=rmodel)
    loop._breviewer._model = bmodel
    for i in range(3):
        loop.on_submit(_get_fake_trajectory())
        print(loop.reviews)
        print(loop.comparisons)
        if i < 2:
            assert loop.retry()
        else:
            assert not loop.retry()
        if i < 2:
            assert loop.get_best() == 0
        else:
            assert loop.get_best() == 2
    assert loop._n_samples == 3


def test_loop_stop_max_fail(dummy_reviewer_config, dummy_binary_reviewer_config):
    rmodel = DeterminedModel(["fail"] * 5)
    # Only have one comparison: The two successes
    bmodel = DeterminedModel(["second"] * 5)
    lconfig = ReviewLoopConfig("ReviewLoop", dummy_reviewer_config, dummy_binary_reviewer_config, max_samples=5)
    loop = ReviewLoop(lconfig, instance={}, model=rmodel)
    loop._breviewer._model = bmodel
    for i in range(5):
        print(i)
        loop.on_submit(_get_fake_trajectory())
        print(loop._reviews)
        if i < 4:
            assert loop.retry()
        else:
            assert not loop.retry()
        assert loop.get_best() == i


@pytest.fixture()
def agent_arguments(dummy_review_loop_config) -> AgentArguments:
    args = AgentArguments(
        model=ModelArguments(model_name="instant_empty_submit"),
        config_file=CONFIG_DIR / "default_from_url.yaml",
        config=None,
    )
    config = args.config
    object.__setattr__(config, "review_loop_config", dummy_review_loop_config)
    object.__setattr__(args, "config", config)
    return args


@pytest.mark.slow()
def test_agent_with_reviewer(agent_arguments, test_env_args):
    assert agent_arguments.config.review_loop_config is not None
    sa = ScriptArguments(
        environment=test_env_args,
        agent=agent_arguments,
        actions=ActionsArguments(),
        print_config=False,
        skip_existing=False,
    )

    class InjectRModelsTests(AgentHook):
        """We need to intercept the initialization of the reviewer as well
        as the run loop of main to inject our models for testing
        as well as the actual tests
        """

        def on_init(self, agent: Agent):
            self._agent = agent

        def on_setup_done(self):
            # Same setup as in test_loop_comparison
            rmodel = DeterminedModel(["success", "fail", "success", "fail"])
            bmodel = DeterminedModel(["second"])
            rloop: ReviewLoop = self._agent._rloop  # type: ignore
            rloop._reviewer._model = rmodel  # type: ignore
            rloop._reviewer._model = bmodel  # type: ignore

        def on_run_done(self, trajectory, info):
            rloop: ReviewLoop = self._agent._rloop  # type: ignore
            assert rloop is not None
            assert rloop._n_samples == 3
            assert rloop.get_best() == 2
            assert info["exit_status"] == "submitted"
            assert info["api_calls"] == 3 * 2

    main = Main(sa)
    main.agent.add_hook(InjectRModelsTests())
    main.main()
