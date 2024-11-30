from __future__ import annotations

from functools import partial

from git import Repo

__version__ = "0.7.0"

from logging import WARNING, getLogger
from pathlib import Path

import swerex.utils.log as log_swerex

from sweagent.utils.log import get_logger

# Monkey patch the logger to use our implementation
log_swerex.get_logger = partial(get_logger, emoji="🦖")

# See https://github.com/princeton-nlp/SWE-agent/issues/585
getLogger("datasets").setLevel(WARNING)
getLogger("numexpr.utils").setLevel(WARNING)

PACKAGE_DIR = Path(__file__).resolve().parent
assert PACKAGE_DIR.is_dir()
REPO_ROOT = PACKAGE_DIR.parent
assert REPO_ROOT.is_dir()
CONFIG_DIR = PACKAGE_DIR.parent / "config"
assert CONFIG_DIR.is_dir()

TOOLS_DIR = PACKAGE_DIR.parent / "tools"
assert TOOLS_DIR.is_dir()

TRAJECTORY_DIR = PACKAGE_DIR.parent / "trajectories"
assert TRAJECTORY_DIR.is_dir()


def get_agent_commit_hash() -> str:
    """Get the commit hash of the current SWE-agent commit.

    If we cannot get the hash, we return an empty string.
    """
    try:
        repo = Repo(REPO_ROOT, search_parent_directories=False)
    except Exception:
        return ""
    return repo.head.object.hexsha


def get_rex_commit_hash() -> str:
    import swerex

    print(swerex.__file__)

    try:
        repo = Repo(Path(swerex.__file__).resolve().parent.parent.parent, search_parent_directories=False)
    except Exception:
        return ""
    return repo.head.object.hexsha


def get_rex_version() -> str:
    from swerex import __version__ as rex_version

    return rex_version


def get_agent_version_info() -> str:
    hash = get_agent_commit_hash()
    rex_hash = get_rex_commit_hash()
    rex_version = get_rex_version()
    return f"This is SWE-agent version {__version__} ({hash}) with SWE-ReX {rex_version} ({rex_hash})."


get_logger("swe-agent", emoji="👋").info(get_agent_version_info())


__all__ = [
    "PACKAGE_DIR",
    "CONFIG_DIR",
    "get_agent_commit_hash",
    "get_agent_version_info",
    "__version__",
]
