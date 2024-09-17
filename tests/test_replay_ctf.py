from __future__ import annotations

import pytest

from run_replay import get_args, main


@pytest.mark.slow
def test_model_replay_from_json(test_trajectories_path, test_data_sources_path):
    traj_path = test_trajectories_path / "ctf" / "pwn" / "warmup.traj"
    assert traj_path.is_file()
    # data_path = test_data_sources_path / "swe-bench-dev-easy_first_only.json"
    # assert data_path.is_file()
    args = [
        "--traj_path",
        str(traj_path),
        # "--data_path",
        # str(data_path),
        "--config_file",
        "config/default_ctf.yaml",
        "--raise_exceptions",
    ]
    args, remaining_args = get_args(args)
    main(**vars(args), forward_args=remaining_args)
