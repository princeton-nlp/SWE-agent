from __future__ import annotations

import sys

import pytest

from run_replay import get_args, main

_TEST_OUTPUTS = {
    "pwn/warmup.traj": r"Closed connection to pwn.chal.csaw.io port 8000\nFLAG{LET_US_BEGIN_CSAW_2016}",
    "forensics/flash.traj": r"the black flag waved night and day from the",
    # "web/i_got_id_demo.traj": r"4365",
    "misc/networking_1.traj": r"Password: \nflag{d316759c281bf925d600be698a4973d5}",
}


@pytest.mark.slow
@pytest.mark.ctf
@pytest.mark.parametrize(
    "traj_rel_path",
    ["pwn/warmup.traj", "forensics/flash.traj", "web/i_got_id_demo.traj", "rev/rock.traj", "misc/networking_1.traj"],
)
def test_ctf_traj_replay(test_ctf_trajectories_path, traj_rel_path, ctf_data_path, capsys):
    if sys.platform == "darwin" and traj_rel_path in ["pwn/warmup.traj", "rev/rock.traj"]:
        pytest.skip("Skipping test on macOS")
    traj_path = test_ctf_trajectories_path / traj_rel_path
    challenge_dir = ctf_data_path / traj_rel_path.removesuffix(".traj")
    assert challenge_dir.is_dir()
    data_path = challenge_dir / "challenge.json"
    assert data_path.is_file()
    assert traj_path.is_file()
    args = [
        "--traj_path",
        str(traj_path),
        "--data_path",
        str(data_path),
        "--repo_path",
        str(challenge_dir),
        "--config_file",
        "config/default_ctf.yaml",
        "--raise_exceptions",
        "--noprint_config",
    ]
    args, remaining_args = get_args(args)
    main(**vars(args), forward_args=remaining_args)
    captured = capsys.readouterr()
    if traj_rel_path in _TEST_OUTPUTS:
        assert _TEST_OUTPUTS[traj_rel_path] in captured.out
