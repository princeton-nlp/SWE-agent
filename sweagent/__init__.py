from __future__ import annotations

__version__ = "0.7.0"

from logging import WARNING, getLogger
from pathlib import Path

# See https://github.com/princeton-nlp/SWE-agent/issues/585
getLogger("datasets").setLevel(WARNING)
getLogger("numexpr.utils").setLevel(WARNING)

PACKAGE_DIR = Path(__file__).resolve().parent
assert PACKAGE_DIR.is_dir()
REPO_ROOT = PACKAGE_DIR.parent
assert REPO_ROOT.is_dir()
CONFIG_DIR = PACKAGE_DIR.parent / "config"
assert CONFIG_DIR.is_dir()


__all__ = [
    "PACKAGE_DIR",
    "CONFIG_DIR",
]
