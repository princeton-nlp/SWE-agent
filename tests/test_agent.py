import pytest
import yaml
from swerex.runtime.abstract import Action, BashObservation, Observation, SweRexception
from swerex.runtime.dummy import DummyRuntime

from sweagent import CONFIG_DIR
from sweagent.agent.agents import Agent, AgentConfig
from sweagent.agent.models import InstantEmptySubmitModelConfig, PredeterminedTestModel
from sweagent.environment.config.problem_statement import EmptyProblemStatement, TextProblemStatement
from sweagent.environment.swe_env import SWEEnv


def test_dummy_env(dummy_env):
    pass


@pytest.fixture
def agent_config():
    return AgentConfig(model=InstantEmptySubmitModelConfig())


@pytest.fixture
def default_agent_config():
    config = yaml.safe_load((CONFIG_DIR / "default.yaml").read_text())
    config["agent"]["model"] = {"name": "instant_empty_submit"}
    print(yaml.dump(config))
    return AgentConfig.model_validate(config["agent"])


@pytest.fixture
def default_agent(default_agent_config: AgentConfig) -> Agent:
    a = Agent.from_config(default_agent_config)
    a.tools.mock_state = {"open_file": "asdf123", "working_dir": "/root"}
    return a


@pytest.fixture
def test_agent(agent_config: AgentConfig) -> Agent:
    return Agent.from_config(agent_config)


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
    assert r.info["exit_status"] == "exit_environment_error"  # type: ignore


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
            raise SweRexception()
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


def test_run_step_by_step_checking_history(dummy_env: SWEEnv, default_agent: Agent, tmp_path):
    a = default_agent
    a.model = PredeterminedTestModel(["asdf", "```\nls\n```", "```\necho 'asdf'\n```", "raise_cost"])  # type: ignore
    a.setup(dummy_env, TextProblemStatement(text="asdf123"))
    dummy_env.deployment.runtime.run_in_session_outputs = [  # type: ignore
        BashObservation(output="file_a file_b"),
        BashObservation(output="asdf"),
    ]
    assert "asdf123" in a._problem_statement.get_problem_statement()  # type: ignore
    # system template and demo and instance template
    assert len(a.local_history) == 3
    system_prompt = a.local_history[0]["content"]
    assert "You are an autonomous programmer" in system_prompt
    demo = a.local_history[1]["content"]
    print(demo)
    assert "demonstration" in demo  # demo
    assert "marshmallow" in demo  # demo
    instance_template = a.local_history[2]["content"]
    assert "the following issue within our repository" in instance_template
    assert "asdf123" in instance_template
    assert len(a.trajectory) == 0
    a.step()
    print(a.trajectory)
    assert len(a.trajectory) == 2  # we requery once because format error
    assert len(a.local_history) == 5  # first action performed + observation
    assert a.local_history[3]["content"].strip() == "```\nls\n```"
    assert "file_a file_b" in a.local_history[4]["content"]
    assert "Open file: asdf123" in a.local_history[4]["content"]
    assert "Current directory: /root" in a.local_history[4]["content"]
    a.step()
    assert len(a.trajectory) == 3
    assert len(a.local_history) == 5  # no message added if done==True
    a.step()
    assert len(a.trajectory) == 4
    assert a.info["exit_status"] == "exit_cost"  # type: ignore


def test_run_autosubmit(dummy_env: SWEEnv, default_agent: Agent, tmp_path):
    a = default_agent
    a.model = PredeterminedTestModel(["raise_cost"])  # type: ignore
    a.setup(dummy_env, EmptyProblemStatement())
    dummy_env.deployment.runtime.run_in_session_outputs = [  # type: ignore
        BashObservation(output=r"<<SUBMISSION||mysubmission||SUBMISSION>>")
    ]
    r = a.step()
    assert a.info is not None
    assert a.info["exit_status"] == "submitted (exit_cost)"  # type: ignore
    assert a.info["submission"] == "mysubmission"  # type: ignore
    assert r.done
    assert r.submission == "mysubmission"
    assert r.exit_status == "submitted (exit_cost)"
    assert not r.action
    assert "cost limit" in r.thought


def test_show_no_output_template(dummy_env: SWEEnv, default_agent: Agent, tmp_path):
    a = default_agent
    a.templates.next_step_no_output_template = "no output template"
    a.setup(dummy_env, EmptyProblemStatement())
    a.model = PredeterminedTestModel(["```\nls\n```", "```\ntest\n```"])  # type: ignore
    dummy_env.deployment.runtime.run_in_session_outputs = [BashObservation(output="")]  # type: ignore
    a.step()
    a.step()
    # todo: actually test that the template is used


def test_successful_submission(dummy_env: SWEEnv, default_agent: Agent, tmp_path):
    a = default_agent
    a.model = PredeterminedTestModel(["```\nsubmit\n```"])  # type: ignore
    a.setup(dummy_env, EmptyProblemStatement())
    dummy_env.deployment.runtime.run_in_session_outputs = BashObservation(output=r"<<SUBMISSION||test||SUBMISSION>>")  # type: ignore
    a.step()
    assert a.info["exit_status"] == "submitted"  # type: ignore
    assert a.info["submission"] == "test"  # type: ignore
    assert a.trajectory[-1]["observation"] == "test"


def test_human_exit(dummy_env: SWEEnv, default_agent: Agent, tmp_path):
    a = default_agent
    a.model = PredeterminedTestModel(["```\nexit\n```"])  # type: ignore
    a.setup(dummy_env, EmptyProblemStatement())
    r = a.step()
    assert r.done
    assert r.exit_status == "exit_command"
    assert r.action.strip() == "exit"
