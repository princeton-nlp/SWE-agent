from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from sweagent import REPO_ROOT
from sweagent.utils.log import get_logger

logger = get_logger("config", emoji="⚙️")


def _convert_path_to_abspath(path: Path | str) -> Path:
    """If path is not absolute, convert it to an absolute path
    using the SWE_AGENT_CONFIG_ROOT environment variable (if set) or
    REPO_ROOT as base.
    """
    path = Path(path)
    root = Path(os.getenv("SWE_AGENT_CONFIG_ROOT", REPO_ROOT))
    assert root.is_dir()
    if not path.is_absolute():
        path = root / path
    assert path.is_absolute()
    return path.resolve()


def _convert_paths_to_abspath(paths: list[Path] | list[str]) -> list[Path]:
    return [_convert_path_to_abspath(p) for p in paths]


def load_environment_variables(path: Path | None = None):
    """Load environment variables from a .env file.
    If path is not provided, we first look for a .env file in the current working
    directory and then in the repository root.
    """
    if path is None:
        cwd_path = Path.cwd() / ".env"
        repo_path = REPO_ROOT / ".env"
        if cwd_path.exists():
            path = cwd_path
        elif repo_path.exists():
            path = REPO_ROOT / ".env"
        else:
            logger.debug("No .env file found")
            return
    if not path.is_file():
        msg = f"No .env file found at {path}"
        raise FileNotFoundError(msg)
    anything_loaded = load_dotenv(dotenv_path=path)
    if anything_loaded:
        logger.info(f"Loaded environment variables from {path}")
