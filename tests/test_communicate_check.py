"""``SWEEnv.communicate`` must forward check='ignore' as SWE-ReX 'ignore'."""

from __future__ import annotations

from types import SimpleNamespace

from sweagent.environment.swe_env import SWEEnv


def test_ignore_does_not_ask_swerex_to_extract_an_exit_code():
    seen: list = []

    async def run_in_session(action):
        seen.append(action)
        return SimpleNamespace(output="ok", exit_code=0)

    env = SWEEnv(
        deployment=SimpleNamespace(runtime=SimpleNamespace(run_in_session=run_in_session)),
        repo=None,
        post_startup_commands=[],
    )
    assert env.communicate("echo hi", check="ignore") == "ok"
    assert env.communicate("echo hi", check="warn") == "ok"
    assert env.communicate("echo hi", check="raise") == "ok"
    assert [action.check for action in seen] == ["ignore", "silent", "silent"]
