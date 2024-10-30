from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import config as config_file
from sweagent import REPO_ROOT
from sweagent.utils.log import get_logger

logger = get_logger("config")


def _convert_path_to_abspath(path: Path | str) -> Path:
    """If path is not absolute, convert it to an absolute path
    using the SWE_AGENT_CONFIG_ROOT environment variable (if set) or
    REPO_ROOT as base.
    """
    path = Path(path)
    root = Path(keys_config.get("SWE_AGENT_CONFIG_ROOT", REPO_ROOT))
    assert root.is_dir()
    if not path.is_absolute():
        path = root / path
    assert path.is_absolute()
    return path.resolve()


def _convert_paths_to_abspath(paths: list[Path] | list[str]) -> list[str]:
    return [str(_convert_path_to_abspath(p)) for p in paths]


class Config:
    def __init__(self, *, keys_cfg_path: Path | None = None):
        """This wrapper class is used to load keys from environment variables or keys.cfg file.
        Whenever both are presents, the environment variable is used.
        """
        if keys_cfg_path is None:
            # Defer import to avoid circular import
            from sweagent import PACKAGE_DIR

            keys_cfg_path = PACKAGE_DIR.parent / "keys.cfg"
        self._keys_cfg = None
        if keys_cfg_path.exists():
            try:
                self._keys_cfg = config_file.Config(str(keys_cfg_path))
            except Exception as e:
                msg = f"Error loading keys.cfg from {keys_cfg_path}. Please check the file."
                raise RuntimeError(msg) from e
        else:
            logger.error(f"keys.cfg not found in {PACKAGE_DIR}")

    def get(self, key: str, default=None, choices: list[Any] | None = None) -> Any:
        """Get a key from environment variables or keys.cfg.

        Args:
            key: The key to retrieve.
            default: The default value to return if the key is not found.
            choices: If provided, the value must be one of the choices.
        """

        def check_choices(value):
            if choices is not None and value not in choices:
                msg = f"Value {value} for key {key} not in {choices}"
                raise ValueError(msg)
            return value

        if key in os.environ:
            return check_choices(os.environ[key])
        if self._keys_cfg is not None and key in self._keys_cfg:
            return check_choices(self._keys_cfg[key])
        return check_choices(default)

    def __getitem__(self, key: str) -> Any:
        if key in os.environ:
            return os.environ[key]
        if self._keys_cfg is not None and key in self._keys_cfg:
            return self._keys_cfg[key]
        msg = f"Key {key} not found in environment variables or keys.cfg (if existing)"
        raise KeyError(msg)

    def __contains__(self, key: str) -> bool:
        return key in os.environ or (self._keys_cfg is not None and key in self._keys_cfg)


keys_config = Config()
