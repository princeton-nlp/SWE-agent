from __future__ import annotations

import copy
import sys
from typing import Any

import pytest

from run_replay import get_args, main

LOG_NOT_CONTAINS_DEFAULT = [
    "Traceback",
    "Exception",
    "socket.gaierror",
]


class ReplayRunValidator:
    def __init__(
        self,
        *,
        log_contains: list[str] | None = None,
        log_not_contains: list[str] | None = None,
        expected_traj: str | None = None,
    ):
        if log_contains is None:
            log_contains = []
        if log_not_contains is None:
            log_not_contains = copy.copy(LOG_NOT_CONTAINS_DEFAULT)
        self._log_contains = log_contains
        self._log_not_contains = log_not_contains + LOG_NOT_CONTAINS_DEFAULT
        self._expected_traj = expected_traj

    def _sanitize_observation(self, observation: str) -> str:
        # exclude everything that looks like a path
        return "\n".join(line for line in observation.splitlines() if "/" not in line).strip()

    def _sanitize_traj(self, traj: dict[str, Any]) -> dict[str, Any]:
        traj = copy.deepcopy(traj)
        # can restore later
        observations = [self._sanitize_observation(t["observation"]) for t in traj["trajectory"]]
        return {"trajectory": observations}

    def __call__(self, stdout: str, traj: str | None = None) -> None:
        for log in self._log_contains:
            assert log in stdout, log
        for log in self._log_not_contains:
            assert log not in stdout, log
        if self._expected_traj is not None:
            assert traj == self._expected_traj


_REPLAY_TESTS = {
    "pwn/warmup.traj": ReplayRunValidator(
        log_contains=[
            "File updated.",
            "Opening connection to pwn.chal.csaw.io on port 8000: Done",
            "Receiving all data",
        ],
    ),
    "forensics/flash.traj": ReplayRunValidator(
        log_contains=["the black flag waved night and day from the"],
    ),
    # "web/i_got_id_demo.traj": r"4365",
    "misc/networking_1.traj": ReplayRunValidator(
        log_contains=["Password: "],
    ),
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
        "--ctf",
    ]
    args, remaining_args = get_args(args)
    main(**vars(args), forward_args=remaining_args)
    captured = capsys.readouterr()
    if traj_rel_path in _REPLAY_TESTS:
        _REPLAY_TESTS[traj_rel_path](stdout=captured.out)
