import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter

from sweagent.environment.config.deployment import DeploymentConfig
from sweagent.environment.config.problem_statement import TextProblemStatement
from sweagent.environment.swe_env import EnvironmentInstanceConfig


class AbstractInstanceSource(ABC):
    """Anything that adheres to this standard can be used to load instances."""

    @abstractmethod
    def get_instance_configs(self) -> list[EnvironmentInstanceConfig]: ...


def _load_file(path: Path) -> Any:
    """Load files based on their extension."""
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_dir():
        from datasets import load_from_disk

        return load_from_disk(path)
    elif path.stem == "json":
        return json.loads(path.read_text())
    elif path.stem == "jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        raise NotImplementedError


def _filter_instances(instances: list[EnvironmentInstanceConfig], filter: str) -> list[EnvironmentInstanceConfig]:
    return [instance for instance in instances if re.match(filter, instance.problem_statement.id)]


class BatchInstance(BaseModel):
    """A single instance in a batch of instances."""

    image_name: str
    problem_statement: str
    id: str

    def _to_env_config(self, deployment_kwargs: dict[str, Any]) -> EnvironmentInstanceConfig:
        """Merge the deployment options into the BatchInstance object to get a full `EnvironmentInstanceConfig`."""
        deployment = TypeAdapter(DeploymentConfig).validate_python(dict(image=self.image_name, **deployment_kwargs))
        problem_statement = TextProblemStatement(problem_statement=self.problem_statement)
        return EnvironmentInstanceConfig(deployment=deployment, problem_statement=problem_statement, repo=None)


class InstancesFromFile(BaseModel, AbstractInstanceSource):
    """Load instances from a file."""

    path: Path
    instance_filter: str = ".*"

    deployment: dict[str, Any]
    """Any options for one of the `DeploymentConfig` subclasses."""

    simple: Literal[True] = True
    """Convenience discriminator for (de)serialization/CLI. Do not change."""

    type: Literal["simple_file"]
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[EnvironmentInstanceConfig]:
        instance_dicts = _load_file(self.path)
        simple_instances = [BatchInstance(**instance_dict) for instance_dict in instance_dicts]
        return [instance._to_env_config(self.deployment) for instance in simple_instances]


class InstancesFromHuggingFace(BaseModel, AbstractInstanceSource):
    """Load instances from HuggingFace."""

    dataset_name: str
    split: str
    instance_filter: str = ".*"

    deployment: dict[str, Any]
    """Any options for one of the `DeploymentConfig` subclasses."""
    type: Literal["simple_huggingface"]
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[EnvironmentInstanceConfig]:
        from datasets import load_dataset

        ds: list[dict[str, Any]] = load_dataset(self.dataset_name, split=self.split)  # type: ignore
        simple_instances: list[BatchInstance] = [BatchInstance(**instance) for instance in ds]
        return [instance._to_env_config(self.deployment) for instance in simple_instances]


class ExpertInstancesFromFile(BaseModel, AbstractInstanceSource):
    """Load instances from a file. The difference to `InstancesFromFile` is that the instances are configured as full
    `EnvironmentInstanceConfig` objects, i.e., we could specify separate deployment configurations etc.
    """

    path: Path
    instance_filter: str = ".*"

    type: Literal["expert_file"]
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[EnvironmentInstanceConfig]:
        instance_dicts = _load_file(self.path)
        instances = [EnvironmentInstanceConfig(**instance_dict) for instance_dict in instance_dicts]
        return _filter_instances(instances, self.instance_filter)


InstanceSourceConfig = ExpertInstancesFromFile | InstancesFromHuggingFace | InstancesFromFile
