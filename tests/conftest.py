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
print("Adjusted path: ", sys.path)


@fixture
def test_trajectory() -> Path:
    traj_dir = _this_dir / "test_data/trajectories/gpt4__klieret__swe-agent-test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1/klieret__swe-agent-test-repo-i1.traj"
    assert traj_dir.exists()
    return json.loads(traj_dir.read_text())