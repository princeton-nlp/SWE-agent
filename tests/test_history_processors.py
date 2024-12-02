import json
from pathlib import Path

from sweagent.agent.history_processors import LastNObservations


def get_history(traj_path: Path):
    return json.loads((traj_path).read_text())["history"]


def count_elided_observations(history: list[dict]):
    return len([entry for entry in history if "Old environment output" in entry["content"]])


def test_last_n_observations(test_trajectories_path: Path):
    history = get_history(
        test_trajectories_path
        / "gpt4__swe-agent-test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1/6e44b9__sweagenttestrepo-1c2844.traj"
    )
    processor = LastNObservations(n=3)
    new_history = processor(history)
    total_observations = len([entry for entry in history if entry["message_type"] == "observation"])
    # extra -1 because instance template is kept
    expected_elided_observations = total_observations - 3 - 1
    assert count_elided_observations(new_history) == expected_elided_observations
