import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, Field, TypeAdapter

from sweagent.environment.config.deployment import DeploymentConfig, LocalDeploymentConfig
from sweagent.environment.config.problem_statement import ProblemStatementConfig, TextProblemStatement
from sweagent.environment.swe_env import EnvironmentConfig


class AbstractInstanceSource(ABC):
    """Anything that adheres to this standard can be used to load instances."""

    @abstractmethod
    def get_instance_configs(self) -> list[EnvironmentConfig]: ...


def _load_file(path: Path) -> Any:
    """Load files based on their extension."""
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_dir():
        from datasets import load_from_disk

        return load_from_disk(path)
    if path.suffix == ".json":
        return json.loads(path.read_text())
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if path.suffix == ".yaml":
        return yaml.safe_load(path.read_text())
    msg = f"Unsupported file extension: {path.suffix}"
    raise NotImplementedError(msg)


class BatchInstance(BaseModel):
    """A single instance in a batch of instances.
    This specifies both the environment configuration and the problem statement.
    """

    env: EnvironmentConfig
    problem_statement: ProblemStatementConfig


def _filter_batch_items(instances: list[BatchInstance], filter: str) -> list[BatchInstance]:
    return [instance for instance in instances if re.match(filter, instance.problem_statement.id)]


class SimpleBatchInstance(BaseModel):
    """A simple way to configure a single instance in a batch of instances that all
    use similar deployment configurations.
    """

    image_name: str
    problem_statement: str
    id: str

    def to_full_batch_instance(self, deployment_kwargs: dict[str, Any]) -> BatchInstance:
        """Merge the deployment options into the `SimpleBatchInstance` object to get a full `BatchInstance`."""
        # Combine image name and deployment options into a DeploymentConfig object. Because this can be one of many
        # subclasses, we use a TypeAdapter to validate/instantiate the object.
        if deployment_kwargs.get("type") == "local":
            if self.image_name:
                msg = "Local deployment does not support image name"
                raise ValueError(msg)
            deployment = LocalDeploymentConfig(**deployment_kwargs)
        else:
            deployment = TypeAdapter(DeploymentConfig).validate_python(dict(image=self.image_name, **deployment_kwargs))
        problem_statement = TextProblemStatement(text=self.problem_statement, id=self.id)
        return BatchInstance(
            env=EnvironmentConfig(deployment=deployment, repo=None), problem_statement=problem_statement
        )


class InstancesFromFile(BaseModel, AbstractInstanceSource):
    """Load instances from a file."""

    path: Path
    filter: str = ".*"

    deployment: dict[str, Any] = Field(default_factory=dict)
    """Any options for one of the `DeploymentConfig` subclasses."""

    simple: Literal[True] = True
    """Convenience discriminator for (de)serialization/CLI. Do not change."""

    type: Literal["file"] = "file"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[BatchInstance]:
        instance_dicts = _load_file(self.path)
        simple_instances = [SimpleBatchInstance(**instance_dict) for instance_dict in instance_dicts]
        instances = [instance.to_full_batch_instance(self.deployment) for instance in simple_instances]
        return _filter_batch_items(instances, self.filter)


class InstancesFromHuggingFace(BaseModel, AbstractInstanceSource):
    """Load instances from HuggingFace."""

    dataset_name: str
    split: str = "dev"
    filter: str = ".*"

    deployment: dict[str, Any]
    """Any options for one of the `DeploymentConfig` subclasses."""
    type: Literal["huggingface"] = "huggingface"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[BatchInstance]:
        from datasets import load_dataset

        ds: list[dict[str, Any]] = load_dataset(self.dataset_name, split=self.split)  # type: ignore
        simple_instances: list[SimpleBatchInstance] = [SimpleBatchInstance(**instance) for instance in ds]
        instances = [instance.to_full_batch_instance(self.deployment) for instance in simple_instances]
        return _filter_batch_items(instances, self.filter)


class SWEBenchInstances(BaseModel, AbstractInstanceSource):
    """Load instances from SWE-bench."""

    flavor: Literal["lite", "verified", "full"] = "lite"

    deployment: dict[str, Any]
    """Any options for one of the `DeploymentConfig` subclasses."""

    type: Literal["swe_bench"] = "swe_bench"
    """Discriminator for (de)serialization/CLI. Do not change."""

    filter: str = ".*"

    def get_instance_configs(self) -> list[BatchInstance]:
        raise NotImplementedError


class ExpertInstancesFromFile(BaseModel, AbstractInstanceSource):
    """Load instances from a file. The difference to `InstancesFromFile` is that the instances are configured as full
    `EnvironmentInstanceConfig` objects, i.e., we could specify separate deployment configurations etc.
    """

    path: Path
    filter: str = ".*"

    type: Literal["expert_file"] = "expert_file"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[BatchInstance]:
        instance_dicts = _load_file(self.path)
        instances = [BatchInstance(**instance_dict) for instance_dict in instance_dicts]
        return _filter_batch_items(instances, self.filter)


BatchInstanceSourceConfig = Annotated[
    InstancesFromHuggingFace | InstancesFromFile | SWEBenchInstances | ExpertInstancesFromFile,
    Field(union_mode="left_to_right"),
]
