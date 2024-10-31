from __future__ import annotations

import logging
import os
from pathlib import PurePath

from rich.logging import RichHandler
from rich.text import Text

_SET_UP_LOGGERS = set()
_ADDITIONAL_HANDLERS = []

logging.TRACE = 5  # type: ignore
logging.addLevelName(logging.TRACE, "TRACE")  # type: ignore


def _interpret_level_from_env(level: str | None, *, default=logging.DEBUG) -> int:
    if not level:
        return default
    if level.isnumeric():
        return int(level)
    return getattr(logging, level.upper())


_STREAM_LEVEL = _interpret_level_from_env(os.environ.get("SWE_AGENT_LOG_STREAM_LEVEL"))
_FILE_LEVEL = _interpret_level_from_env(os.environ.get("SWE_AGENT_LOG_FILE_LEVEL"), default=logging.TRACE)


class _RichHandlerWithEmoji(RichHandler):
    def __init__(self, emoji: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not emoji.endswith(" "):
            emoji += " "
        self.emoji = emoji

    def get_level_text(self, record: logging.LogRecord) -> Text:
        level_name = record.levelname
        return Text.styled((self.emoji + level_name).ljust(10), f"logging.level.{level_name.lower()}")


def get_logger(name: str, *, emoji: str = "") -> logging.Logger:
    """Get logger. Use this instead of `logging.getLogger` to ensure
    that the logger is set up with the correct handlers.
    """
    logger = logging.getLogger(name)
    if name in _SET_UP_LOGGERS:
        # Already set up
        return logger
    handler = _RichHandlerWithEmoji(
        emoji=emoji,
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
