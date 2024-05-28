from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import config as config_file

logger = logging.getLogger("config")


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

    def get(self, key: str, default=None) -> Any:
        if key in os.environ:
            return os.environ[key]
        if self._keys_cfg is not None and key in self._keys_cfg:
            return self._keys_cfg[key]
        return default

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
