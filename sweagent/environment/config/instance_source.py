from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from sweagent.environment.swe_env import EnvironmentInstanceConfig


class AbstractInstanceSource(ABC):
    @abstractmethod
    def get_instance_configs(self) -> list[EnvironmentInstanceConfig]: ...


class JSONInstances(BaseModel, AbstractInstanceSource):
    path: Path
    instance_filter: str = ".*"

    def get_instance_configs(self) -> list[EnvironmentInstanceConfig]: ...


class HuggingfaceInstances(BaseModel, AbstractInstanceSource):
    dataset_name: str
    split: str
    instance_filter: str = ".*"

    def get_instance_configs(self) -> list[EnvironmentInstanceConfig]: ...


InstanceSourceConfig = JSONInstances | HuggingfaceInstances
