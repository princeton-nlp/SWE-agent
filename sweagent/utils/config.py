from __future__ import annotations

import logging
import os
from typing import Any

import config as config_file

logger = logging.getLogger("config")


class Config:
    def __init__(
        self,
    ):
        """This wrapper class is used to load keys from environment variables or keys.cfg file.
        Whenever both are presents, the environment variable is used.
        """
        # Defer import to avoid circular import
        from sweagent import PACKAGE_DIR

        self._keys_cfg = None
        keys_cfg_path = PACKAGE_DIR / "keys.cfg"
        if keys_cfg_path.exists():
            try:
                self._keys_cfg = config_file.Config(PACKAGE_DIR / "keys.cfg")
            except Exception as e:
                raise RuntimeError(f"Error loading keys.cfg. Please check the file.") from e
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
        raise KeyError(f"Key {key} not found in environment or keys.cfg")

    def __contains__(self, key: str) -> bool:
        return key in os.environ or (self._keys_cfg is not None and key in self._keys_cfg)
