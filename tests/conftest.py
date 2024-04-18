import os
import json
import sys
from pathlib import Path

from pytest import fixture

# this is a hack and should be removed when we have a better solution
_this_dir = Path(__file__).resolve().parent
root_dir = _this_dir.parent 
package_dir = root_dir / "sweagent"
sys.path.insert(0, str(root_dir))
sys.path.insert(1, str(package_dir))
os.environ["SWE_AGENT_EXPERIMENTAL_COMMUNICATE"] = "1"


@fixture
def test_data_path() -> Path:
    p = _this_dir / "test_data"
    assert p.is_dir()
    return p

@fixture
def test_trajectories_path(test_data_path) -> Path:
    p = test_data_path / "trajectories"
    assert p.is_dir()
    return p


@fixture
def test_data_sources_path(test_data_path) -> Path:
    p = test_data_path / "data_sources"
    assert p.is_dir()
    return p

@fixture
def test_trajectory_path(test_trajectories_path) -> Path:
    traj = test_trajectories_path / "gpt4__klieret__swe-agent-test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1" / "klieret__swe-agent-test-repo-i1.traj"
    assert traj.exists()
    return traj

@fixture
def test_trajectory(test_trajectory_path):
    return json.loads(test_trajectory_path.read_text())
