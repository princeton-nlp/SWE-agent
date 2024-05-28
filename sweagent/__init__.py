from __future__ import annotations

__version__ = "0.2.0"

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
assert PACKAGE_DIR.is_dir()
CONFIG_DIR = PACKAGE_DIR.parent / "config"
assert CONFIG_DIR.is_dir()


__all__ = [
    "PACKAGE_DIR",
    "CONFIG_DIR",
]
