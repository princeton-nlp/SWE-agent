import json
import random
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from swerex.deployment.config import (
    DeploymentConfig,
    DockerDeploymentConfig,
    DummyDeploymentConfig,
    LocalDeploymentConfig,
)
from typing_extensions import Self

from sweagent.environment.config.problem_statement import ProblemStatementConfig, TextProblemStatement
from sweagent.environment.config.repo import PreExistingRepo
from sweagent.environment.swe_env import EnvironmentConfig
from sweagent.utils.log import get_logger

logger = get_logger("swea-config", emoji="🔧")


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


def _slice_spec_to_slice(slice_spec: str) -> slice:
    if slice_spec == "":
        return slice(None)
    parts = slice_spec.split(":")
    if len(parts) == 1:
        return slice(int(parts[0]))
    if len(parts) == 2:
        return slice(int(parts[0]), int(parts[1]))
    if len(parts) == 3:
        return slice(int(parts[0]), int(parts[1]), int(parts[2]))
    msg = (
        f"Invalid slice specification: {slice_spec!r}. "
        "Here's the expected format: stop or start:stop or start:stop:step "
        "(i.e., it behaves exactly like python's list slicing `list[slice]`)."
    )
    raise ValueError(msg)


def _filter_batch_items(
    instances: list[BatchInstance], *, filter_: str, slice_: str = "", shuffle: bool = False
) -> list[BatchInstance]:
    if shuffle:
        instances = instances.copy()
        random.seed(42)
        random.shuffle(instances)
    before_filter = len(instances)
    instances = [instance for instance in instances if re.match(filter_, instance.problem_statement.id)]
    after_filter = len(instances)
    if before_filter != after_filter:
        logger.info("Instance filter: %d -> %d instances", before_filter, after_filter)
    if slice_:
        instances = instances[_slice_spec_to_slice(slice_)]
        after_slice = len(instances)
        if before_filter != after_slice:
            logger.info("Instance slice: %d -> %d instances", before_filter, after_slice)
    return instances


class SimpleBatchInstance(BaseModel):
    """A simple way to configure a single instance in a batch of instances that all
    use similar deployment configurations.

    Predominantly used for benchmarking purposes. Assumes that the repository is already
    present in the docker container.
    """

    image_name: str
    problem_statement: str
    id: str
    repo_name: str = ""
    """The repo name or path within the docker container/environment."""
    base_commit: str = "HEAD"
    """Used to reset repo."""

    def to_full_batch_instance(self, deployment: DeploymentConfig) -> BatchInstance:
        """Merge the deployment options into the `SimpleBatchInstance` object to get a full `BatchInstance`."""
        # Combine image name and deployment options into a DeploymentConfig object. Because this can be one of many
        # subclasses, we use a TypeAdapter to validate/instantiate the object.
        # Very important: Make a copy of the deployment config because it will be shared among instances!!!
        deployment = deployment.model_copy()
        problem_statement = TextProblemStatement(text=self.problem_statement, id=self.id)
        if self.repo_name:
            repo = PreExistingRepo(repo_name=self.repo_name, base_commit=self.base_commit)
        else:
            repo = None
        if isinstance(deployment, LocalDeploymentConfig):
            if self.image_name:
                msg = "Local deployment does not support image_name"
                raise ValueError(msg)
            return BatchInstance(
                env=EnvironmentConfig(deployment=deployment, repo=repo), problem_statement=problem_statement
            )
        if isinstance(deployment, DummyDeploymentConfig):
            return BatchInstance(
                env=EnvironmentConfig(deployment=deployment, repo=repo), problem_statement=problem_statement
            )
        deployment.image = self.image_name  # type: ignore
        return BatchInstance(
            env=EnvironmentConfig(deployment=deployment, repo=repo), problem_statement=problem_statement
        )

    @classmethod
    def from_swe_bench(cls, instance: dict[str, Any]) -> Self:
        """Convert instances from the classical SWE-bench dataset to the `SimpleBatchInstance` format."""
        iid = instance["instance_id"]
        # Docker doesn't allow double underscore, so we replace them with a magic token
        id_docker_compatible = iid.replace("__", "_1776_")
        image_name = f"swebench/sweb.eval.x86_64.{id_docker_compatible}:v1"
        return cls(
            image_name=image_name,
            problem_statement=instance["problem_statement"],
            id=iid,
            repo_name="testbed",
            base_commit=instance["base_commit"],
        )


class InstancesFromFile(BaseModel, AbstractInstanceSource):
    """Load instances from a file."""

    path: Path
    filter: str = ".*"
    """Regular expression to filter the instances by instance id."""
    slice: str = ""
    """Select only a slice of the instances (after filtering by `filter`).
    Possible values are stop or start:stop or start:stop:step
    (i.e., it behaves exactly like python's list slicing `list[slice]`).
    """
    shuffle: bool = False
    """Shuffle the instances (before filtering and slicing)."""

    deployment: DeploymentConfig = Field(
        default_factory=lambda: DockerDeploymentConfig(image="python:3.11"),
        description="Deployment options.",
    )
    """Note that the image_name option is overwritten by the images specified in the task instances."""

    simple: Literal[True] = True
    """Convenience discriminator for (de)serialization/CLI. Do not change."""

    type: Literal["file"] = "file"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[BatchInstance]:
        instance_dicts = _load_file(self.path)
        simple_instances = [SimpleBatchInstance.model_validate(instance_dict) for instance_dict in instance_dicts]
        instances = [instance.to_full_batch_instance(self.deployment) for instance in simple_instances]
        return _filter_batch_items(instances, filter_=self.filter, slice_=self.slice, shuffle=self.shuffle)

    @property
    def id(self) -> str:
        return self.path.stem


class InstancesFromHuggingFace(BaseModel, AbstractInstanceSource):
    """Load instances from HuggingFace."""

    dataset_name: str
    split: str = "dev"
    filter: str = ".*"
    """Regular expression to filter the instances by instance id."""
    slice: str = ""
    """Select only a slice of the instances (after filtering by `filter`).
    Possible values are stop or start:stop or start:stop:step.
    (i.e., it behaves exactly like python's list slicing `list[slice]`).
    """
    shuffle: bool = False
    """Shuffle the instances (before filtering and slicing)."""

    deployment: DeploymentConfig = Field(
        default_factory=lambda: DockerDeploymentConfig(image="python:3.11"),
        description="Deployment options.",
    )
    """Deployment configuration. Note that the image_name option is overwritten by the images specified in the task instances.
    """
    type: Literal["huggingface"] = "huggingface"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[BatchInstance]:
        from datasets import load_dataset

        ds: list[dict[str, Any]] = load_dataset(self.dataset_name, split=self.split)  # type: ignore
        simple_instances: list[SimpleBatchInstance] = [SimpleBatchInstance.model_validate(instance) for instance in ds]
        instances = [instance.to_full_batch_instance(self.deployment) for instance in simple_instances]
        return _filter_batch_items(instances, filter_=self.filter, slice_=self.slice, shuffle=self.shuffle)

    @property
    def id(self) -> str:
        return "".join(l for l in self.dataset_name if l.isalnum())


class SWEBenchInstances(BaseModel, AbstractInstanceSource):
    """Load instances from SWE-bench."""

    flavor: Literal["lite", "verified", "full"] = "lite"

    split: Literal["dev", "test"] = "dev"

    deployment: DeploymentConfig = Field(
        default_factory=lambda: DockerDeploymentConfig(image="python:3.11"),
        description="Deployment options.",
    )
    """Deployment configuration. Note that the image_name option is overwritten by the images specified in the task instances.
    """

    type: Literal["swe_bench"] = "swe_bench"
    """Discriminator for (de)serialization/CLI. Do not change."""

    filter: str = ".*"
    """Regular expression to filter the instances by instance id."""
    slice: str = ""
    """Select only a slice of the instances (after filtering by `filter`).
    Possible values are stop or start:stop or start:stop:step.
    (i.e., it behaves exactly like python's list slicing `list[slice]`).
    """
    shuffle: bool = False
    """Shuffle the instances (before filtering and slicing)."""

    def _get_huggingface_name(self) -> str:
        if self.flavor == "full":
            return "princeton-nlp/SWE-Bench"
        elif self.flavor == "verified":
            return "princeton-nlp/SWE-Bench_Verified"
        elif self.flavor == "lite":
            return "princeton-nlp/SWE-Bench_Lite"
        msg = f"Unsupported flavor: {self.flavor}"
        raise ValueError(msg)

    def get_instance_configs(self) -> list[BatchInstance]:
        from datasets import load_dataset

        ds: list[dict[str, Any]] = load_dataset(self._get_huggingface_name(), split=self.split)  # type: ignore
        instances = [
            SimpleBatchInstance.from_swe_bench(instance).to_full_batch_instance(self.deployment) for instance in ds
        ]
        return _filter_batch_items(instances, filter_=self.filter, slice_=self.slice, shuffle=self.shuffle)

    @property
    def id(self) -> str:
        return f"swe_bench_{self.flavor}"


class ExpertInstancesFromFile(BaseModel, AbstractInstanceSource):
    """Load instances from a file. The difference to `InstancesFromFile` is that the instances are configured as full
    `EnvironmentInstanceConfig` objects, i.e., we could specify separate deployment configurations etc.
    """

    path: Path
    filter: str = ".*"
    """Regular expression to filter the instances by instance id."""
    slice: str = ""
    """Select only a slice of the instances (after filtering by `filter`).
    Possible values are stop or start:stop or start:stop:step.
    (i.e., it behaves exactly like python's list slicing `list[slice]`).
    """
    shuffle: bool = False
    """Shuffle the instances (before filtering and slicing)."""

    type: Literal["expert_file"] = "expert_file"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_instance_configs(self) -> list[BatchInstance]:
        instance_dicts = _load_file(self.path)
        instances = [BatchInstance.model_validate(instance_dict) for instance_dict in instance_dicts]
        return _filter_batch_items(instances, filter_=self.filter, slice_=self.slice, shuffle=self.shuffle)

    @property
    def id(self) -> str:
        return self.path.stem


BatchInstanceSourceConfig = InstancesFromHuggingFace | InstancesFromFile | SWEBenchInstances | ExpertInstancesFromFile
