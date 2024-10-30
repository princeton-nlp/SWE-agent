from typing import Literal

from pydantic import BaseModel


class LocalDeploymentConfig(BaseModel):
    type: Literal["local"] = "local"
    """Discriminator for (de)serialization/CLI. Do not change."""


class DockerDeploymentConfig(BaseModel):
    """Configuration for the deployment of the environment"""

    image: str = "sweagent/swe-agent:latest"

    type: Literal["docker"] = "docker"
    """Discriminator for (de)serialization/CLI. Do not change."""


class ModalDeploymentConfig(BaseModel):
    image: str = "sweagent/swe-agent:latest"

    type: Literal["modal"] = "modal"
    """Discriminator for (de)serialization/CLI. Do not change."""


DeploymentConfig = DockerDeploymentConfig | ModalDeploymentConfig | LocalDeploymentConfig
