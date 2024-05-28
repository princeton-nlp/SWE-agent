from __future__ import annotations

__version__ = "0.2.0"

from pathlib import Path

from sweagent.agent.agents import (
    Agent,
    AgentArguments,
)
from sweagent.agent.models import (
    ModelArguments,
)
from sweagent.environment.swe_env import (
    EnvironmentArguments,
    SWEEnv,
)
from sweagent.environment.utils import (
    get_data_path_name,
)

PACKAGE_DIR = Path(__file__).resolve().parent
assert PACKAGE_DIR.is_dir()
CONFIG_DIR = PACKAGE_DIR.parent / "config"
assert CONFIG_DIR.is_dir()


__all__ = [
    "Agent",
    "AgentArguments",
    "ModelArguments",
    "EnvironmentArguments",
    "SWEEnv",
    "get_data_path_name",
    "PACKAGE_DIR",
    "CONFIG_DIR",
]
