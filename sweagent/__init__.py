from __future__ import annotations

from git import Repo

__version__ = "0.7.0"

from logging import WARNING, getLogger
from pathlib import Path

import swerex.utils.log as log_swerex

from sweagent.utils.log import get_logger

# Monkey patch the logger to use our implementation
log_swerex.get_logger = get_logger

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


def get_agent_commit_hash() -> str:
    repo = Repo(REPO_ROOT, search_parent_directories=True)
    return repo.head.object.hexsha


def get_agent_version_info() -> str:
    try:
        hash = get_agent_commit_hash()
    except Exception:
        hash = "unknown"
    return f"This is SWE-agent version {__version__} with commit hash {hash}."


getLogger("swe-agent").info(get_agent_version_info())


__all__ = [
    "PACKAGE_DIR",
    "CONFIG_DIR",
    "get_agent_commit_hash",
    "get_agent_version_info",
    "__version__",
]
