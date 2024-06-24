from __future__ import annotations

import logging
import os
from pathlib import PurePath

from rich.logging import RichHandler

_SET_UP_LOGGERS = set()
_ADDITIONAL_HANDLERS = []

logging.TRACE = 5  # type: ignore
logging.addLevelName(logging.TRACE, "TRACE")  # type: ignore


def _interpret_level_from_env(level: str | None) -> int:
    if not level:
        return logging.DEBUG
    if level.isnumeric():
        return int(level)
    return getattr(logging, level.upper(), logging.DEBUG)


_STREAM_LEVEL = _interpret_level_from_env(os.environ.get("SWE_AGENT_LOG_STREAM_LEVEL"))
_FILE_LEVEL = _interpret_level_from_env(os.environ.get("SWE_AGENT_LOG_FILE_LEVEL"))


def get_logger(name: str) -> logging.Logger:
    """Get logger. Use this instead of `logging.getLogger` to ensure
    that the logger is set up with the correct handlers.
    """
    logger = logging.getLogger(name)
    if name in _SET_UP_LOGGERS:
        # Already set up
        return logger
    handler = RichHandler(
        show_time=bool(os.environ.get("SWE_AGENT_LOG_TIME", False)),
        show_path=False,
    )
    handler.setLevel(_STREAM_LEVEL)
    logger.setLevel(min(_STREAM_LEVEL, _FILE_LEVEL))
    logger.addHandler(handler)
    logger.propagate = False
    _SET_UP_LOGGERS.add(name)
    for handler in _ADDITIONAL_HANDLERS:
        logger.addHandler(handler)
    return logger


def add_file_handler(path: PurePath | str) -> None:
    """Adds a file handler to all loggers that we have set up
    and all future loggers that will be set up with `get_logger`.
    """
    handler = logging.FileHandler(path)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(_FILE_LEVEL)
    for name in _SET_UP_LOGGERS:
        logger = logging.getLogger(name)
        logger.addHandler(handler)
    _ADDITIONAL_HANDLERS.append(handler)


default_logger = get_logger("swe-agent")
