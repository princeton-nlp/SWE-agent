from run_replay import get_args, main
import pytest

@pytest.mark.slow
def test_model_replay():
    # fixme: might make sure that path to test data is independent of CWD
    args = [
        "--traj_path",
        "tests/test_data/trajectories/gpt4__klieret__swe-agent-test-repo__default_from_url__t-0.00__p-0.95__c-3.00__install-1/klieret__swe-agent-test-repo-i1.traj",
        "--data_path",
        "https://github.com/klieret/swe-agent-test-repo/issues/1",
        "--config_file",
        "config/default_from_url.yaml",
        "--raise_exceptions=True",
    ]
    args, remaining_args = get_args(args)
    main(**vars(args), forward_args=remaining_args)