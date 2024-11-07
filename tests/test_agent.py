import pytest
from swerex.runtime.abstract import Action, Observation
from swerex.runtime.dummy import DummyRuntime

from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import ModelConfig, PredeterminedTestModel
from sweagent.environment.config.problem_statement import EmptyProblemStatement
from sweagent.environment.swe_env import SWEEnv


def test_dummy_env(dummy_env):
    pass


@pytest.fixture
def agent_config():
    return AgentConfig(model=ModelConfig(name="instant_empty_submit"))


@pytest.fixture
def test_agent(agent_config: AgentConfig) -> Agent:
    return Agent.from_config(agent_config)


def test_exit_cost_manually_raised(dummy_env: SWEEnv, test_agent: Agent, tmp_path):
    test_agent.model = PredeterminedTestModel(["```\nexit_cost\n```"])  # type: ignore
    r = test_agent.run(
        problem_statement=EmptyProblemStatement(),
        env=dummy_env,
        output_dir=tmp_path,
    )
    assert r.info["exit_status"] == "exit_cost"  # type: ignore


def test_exit_cost(dummy_env: SWEEnv, test_agent: Agent, tmp_path):
    test_agent.model = PredeterminedTestModel(["raise_cost"])  # type: ignore
    r = test_agent.run(
        problem_statement=EmptyProblemStatement(),
        env=dummy_env,
        output_dir=tmp_path,
    )
    assert r.info["exit_status"] == "exit_cost"  # type: ignore


def test_exit_context(dummy_env: SWEEnv, test_agent: Agent, tmp_path):
    test_agent.model = PredeterminedTestModel(["raise_context"])  # type: ignore
    r = test_agent.run(
        problem_statement=EmptyProblemStatement(),
        env=dummy_env,
        output_dir=tmp_path,
    )
    assert r.info["exit_status"] == "exit_context"  # type: ignore


def test_exit_model_error(dummy_env: SWEEnv, test_agent: Agent, tmp_path):
    test_agent.model = PredeterminedTestModel(["raise_runtime"])  # type: ignore
    r = test_agent.run(
        problem_statement=EmptyProblemStatement(),
        env=dummy_env,
        output_dir=tmp_path,
    )
    assert r.info["exit_status"] == "exit_error"  # type: ignore


def test_exit_format(dummy_env: SWEEnv, test_agent: Agent, tmp_path):
    test_agent.model = PredeterminedTestModel(["a", "b", "c", "d"])  # type: ignore
    r = test_agent.run(
        problem_statement=EmptyProblemStatement(),
        env=dummy_env,
        output_dir=tmp_path,
    )
    assert r.info["exit_status"] == "exit_format"  # type: ignore


def test_exit_blocklist(dummy_env: SWEEnv, test_agent: Agent, tmp_path):
    test_agent.model = PredeterminedTestModel(["```\nvim\n```", "```\npython\n```", "```\nsu\n```", "```\nnano\n```"])  # type: ignore
    r = test_agent.run(
        problem_statement=EmptyProblemStatement(),
        env=dummy_env,
        output_dir=tmp_path,
    )
    assert r.info["exit_status"] == "exit_format"  # type: ignore


class RuntimeRaisesFirst(DummyRuntime):
    async def run_in_session(self, action: Action) -> Observation:
        if action.session_type == "bash" and action.command == "raise":
            raise RuntimeError()
        return await super().run_in_session(action)


def test_early_exit(dummy_env: SWEEnv, test_agent: Agent, tmp_path):
    test_agent.model = PredeterminedTestModel(["```\nraise\n```"])  # type: ignore
    test_agent._catch_errors = True
    dummy_env.deployment.runtime = RuntimeRaisesFirst()  # type: ignore
    r = test_agent.run(
        problem_statement=EmptyProblemStatement(),
        env=dummy_env,
        output_dir=tmp_path,
    )
    assert r.info["exit_status"] == "exit_environment_error"  # type: ignore
