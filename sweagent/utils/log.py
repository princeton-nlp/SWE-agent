from __future__ import annotations

import logging
import os

from rich.logging import RichHandler

_SET_UP_LOGGERS = set()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if name in _SET_UP_LOGGERS:
        # Already set up
        return logger
    handler = RichHandler(
        show_time=bool(os.environ.get("SWE_AGENT_LOG_TIME", False)),
        show_path=False,
    )
    handler.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
    _SET_UP_LOGGERS.add(name)
    return logger


default_logger = get_logger("swe-agent")
