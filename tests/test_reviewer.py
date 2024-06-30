from __future__ import annotations

import json
import pprint

import pytest

from run import ActionsArguments, Main, ScriptArguments
from sweagent import CONFIG_DIR
from sweagent.agent.agents import Agent, AgentArguments, AgentHook
from sweagent.agent.models import BaseModel, ModelArguments
from sweagent.agent.reviewer import (
    BinaryReviewer,
    BinaryReviewerConfig,
    GTCConfig,
    Reviewer,
    ReviewerConfig,
    ReviewLoop,
    ReviewLoopConfig,
    get_review_loop_from_config,
)
from sweagent.types import ReviewerResult, ReviewSubmission


@pytest.fixture()
def dummy_reviewer_config() -> ReviewerConfig:
    return ReviewerConfig("system_template", "instance_template")


@pytest.fixture()
def dummy_binary_reviewer_config() -> BinaryReviewerConfig:
    return BinaryReviewerConfig("system_template", "instance_template")


@pytest.fixture()
def dummy_review_loop_config(dummy_reviewer_config, dummy_binary_reviewer_config) -> ReviewLoopConfig:
    return ReviewLoopConfig(
        review_loop_classname="ReviewLoop",
        reviewer_classname="Reviewer",
        reviewer_config=dummy_reviewer_config,
        binary_reviewer_config=dummy_binary_reviewer_config,
    )


class DeterminedModel(BaseModel):
    MODELS = {
        "determined_model": {
            "max_context": 100_000,
            "max_tokens_to_sample": 4096,
            "cost_per_input_token": 0,
            "cost_per_output_token": 0,
        }
    }

    def __init__(self, replies: list[str]):
        ma = ModelArguments("determined_model")
        super().__init__(ma, [])  # type: ignore
        self._replies = replies
        self._idx = 0

    def query(self, messages):
        reply = self._replies[self._idx]
        self._idx += 1
        self.update_stats(0, 0)
        return reply


def test_determined_model_costs():
    model = DeterminedModel([""])
    assert model.stats.api_calls == 0
    model.query([{"role": "system", "content": ""}])
    assert model.stats.api_calls == 1


def test_get_from_config(dummy_review_loop_config):
    get_review_loop_from_config(dummy_review_loop_config, instance={}, model=DeterminedModel([]))


def test_reviewer(dummy_reviewer_config):
    model = DeterminedModel(["success", "fail", "false", ""])
    reviewer = Reviewer(dummy_reviewer_config, model)
    instance = {}
    submission = _get_fake_submission()
    assert reviewer.review(instance, submission).accept
    assert not reviewer.review(instance, submission).accept
    assert not reviewer.review(instance, submission).accept
    assert not reviewer.review(instance, submission).accept


def test_reviewer_reject_no_exit(dummy_reviewer_config):
    model = DeterminedModel([])
    reviewer = Reviewer(dummy_reviewer_config, model)
    sub = _get_fake_submission()
    del sub.info["exit_status"]
    assert not reviewer.review({}, sub).accept


def test_reviewer_reject_exit_cost(dummy_reviewer_config):
    model = DeterminedModel([])
    reviewer = Reviewer(dummy_reviewer_config, model)
    sub = _get_fake_submission(exit_status="submitted (exit_cost)")
    assert not reviewer.review({}, sub).accept


def _get_fake_submission(exit_status="submitted"):
    return ReviewSubmission(
        trajectory=[],
        info={"exit_status": exit_status},
    )


def test_binary_reviewer(dummy_binary_reviewer_config):
    model = DeterminedModel(["first", "second", "false", ""])
    br = BinaryReviewer(dummy_binary_reviewer_config, model)
    instance = {}
    sub1 = _get_fake_submission()
    osub2 = _get_fake_submission()
    drr = ReviewerResult(True, "", [])
    assert br.compare_submissions(instance, sub1, osub2, drr, drr).choice == 0
    assert br.compare_submissions(instance, sub1, osub2, drr, drr).choice == 1
    assert br.compare_submissions(instance, sub1, osub2, drr, drr).choice == 0
    assert br.compare_submissions(instance, sub1, osub2, drr, drr).choice == 0


def test_loop_comparison_quit_after_max_accepted(dummy_reviewer_config, dummy_binary_reviewer_config):
    rmodel = DeterminedModel(["success", "fail", "success", "fail"])
    # Only have one comparison: The two successes
    bmodel = DeterminedModel(["second"])
    lconfig = ReviewLoopConfig(
        review_loop_classname="ReviewLoop",
        reviewer_classname="Reviewer",
        reviewer_config=dummy_reviewer_config,
        binary_reviewer_classname="BinaryReviewer",
        binary_reviewer_config=dummy_binary_reviewer_config,
        max_samples=100,
        min_draws=100,
        max_accepted_draws=2,
    )
    loop = ReviewLoop(lconfig, instance={}, model=rmodel)
    loop._breviewer._model = bmodel
    for i in range(3):
        loop.on_submit(_get_fake_submission())
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
    assert rmodel.stats.api_calls == 3
    assert bmodel.stats.api_calls == 1


def test_loop_comparison_quit_after_accept(dummy_reviewer_config, dummy_binary_reviewer_config):
    rmodel = DeterminedModel(["fail", "fail", "success"])
    # Only have one comparison: The two fails
    bmodel = DeterminedModel(["second"])
    lconfig = ReviewLoopConfig(
        review_loop_classname="ReviewLoop",
        reviewer_classname="Reviewer",
        reviewer_config=dummy_reviewer_config,
        binary_reviewer_classname="BinaryReviewer",
        binary_reviewer_config=dummy_binary_reviewer_config,
        max_samples=100,
    )
    loop = ReviewLoop(lconfig, instance={}, model=rmodel)
    loop._breviewer._model = bmodel
    for i in range(3):
        loop.on_submit(_get_fake_submission())
        print(loop.reviews)
        print(loop.comparisons)
        if i < 2:
            assert loop.retry()
        else:
            assert not loop.retry()
        assert loop.get_best() == i
    assert loop._n_samples == 3
    assert rmodel.stats.api_calls == 3
    assert bmodel.stats.api_calls == 1


def test_loop_stop_max_fail(dummy_reviewer_config, dummy_binary_reviewer_config):
    rmodel = DeterminedModel(["fail"] * 5)
    # Only have one comparison: The two successes
    bmodel = DeterminedModel(["second"] * 4)
    lconfig = ReviewLoopConfig(
        "ReviewLoop",
        reviewer_classname="Reviewer",
        binary_reviewer_classname="BinaryReviewer",
        reviewer_config=dummy_reviewer_config,
        binary_reviewer_config=dummy_binary_reviewer_config,
        max_samples=5,
    )
    loop = ReviewLoop(lconfig, instance={}, model=rmodel)
    loop._breviewer._model = bmodel
    for i in range(5):
        print(i)
        loop.on_submit(_get_fake_submission())
        print(loop._reviews)
        if i < 4:
            assert loop.retry()
        else:
            assert not loop.retry()
        assert loop.get_best() == i
    assert rmodel.stats.api_calls == 5
    assert bmodel.stats.api_calls == 4


def get_agent_arguments(review_loop_config) -> AgentArguments:
    args = AgentArguments(
        model=ModelArguments(model_name="instant_empty_submit"),
        config_file=CONFIG_DIR / "default_from_url.yaml",
        config=None,
    )
    config = args.config
    object.__setattr__(config, "review_loop_config", review_loop_config)
    object.__setattr__(args, "config", config)
    return args


@pytest.mark.slow()
def test_agent_with_reviewer(dummy_reviewer_config, dummy_binary_reviewer_config, test_env_args):
    rl_config = ReviewLoopConfig(
        review_loop_classname="ReviewLoop",
        reviewer_classname="Reviewer",
        binary_reviewer_classname="BinaryReviewer",
        reviewer_config=dummy_reviewer_config,
        binary_reviewer_config=dummy_binary_reviewer_config,
        gtc_classname="GraveToCradle",
        gtc_config=GTCConfig(),
        max_samples=100,
        min_draws=100,
        max_accepted_draws=2,
    )
    agent_args = get_agent_arguments(rl_config)
    assert agent_args.config.review_loop_config is not None
    sa = ScriptArguments(
        environment=test_env_args,
        agent=agent_args,
        actions=ActionsArguments(),
        print_config=False,
        skip_existing=False,
        raise_exceptions=True,
    )

    class InjectRModelsTests(AgentHook):
        """We need to intercept the initialization of the reviewer as well
        as the run loop of main to inject our models for testing
        as well as the actual tests
        """

        def on_init(self, agent: Agent):
            self._agent = agent
            print("hook initialized")

        def on_setup_done(self):
            # Same setup as in test_loop_comparison
            model = DeterminedModel(["success", "fail", "success", "second"])
            rloop: ReviewLoop = self._agent._rloop  # type: ignore
            rloop._reviewer._model = model  # type: ignore
            rloop._breviewer._model = model  # type: ignore
            rloop._model = model

        def on_run_done(self, trajectory, info):
            rloop: ReviewLoop = self._agent._rloop  # type: ignore
            assert rloop is not None
            assert rloop._n_samples == 3
            assert rloop.get_best() == 2
            assert info["exit_status"] == "submitted"
            assert info["model_stats"]["api_calls"] == 2

    main = Main(sa)
    main.agent.add_hook(InjectRModelsTests())
    # main.agent.logger.setLevel(logging.ERROR)
    main.main()
    assert main.agent._rloop.model_stats.api_calls == 4
    full_info = json.loads(main.agent.traj_path.read_text())  # type: ignore
    full_info["attempts"] = [
        {k: v for k, v in attempt.items() if k not in ["trajectory", "history"]} for attempt in full_info["attempts"]
    ]
    del full_info["trajectory"]
    del full_info["history"]
    pprint.pprint(full_info)
    assert len(full_info["attempts"]) == 3
    assert full_info["info"]["model_stats"]["api_calls"] == 3 * 2 + 4
