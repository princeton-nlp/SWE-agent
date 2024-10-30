from typing import Literal

from pydantic import BaseModel


class DockerDeploymentConfig(BaseModel):
    """Configuration for the deployment of the environment"""

    image: str = "sweagent/swe-agent:latest"

    type: Literal["docker"] = "docker"
    """Discriminator for serialization. Do not change."""


class ModalDeploymentConfig(BaseModel):
    image: str = "sweagent/swe-agent:latest"

    type: Literal["modal"] = "modal"
    """Discriminator for serialization. Do not change."""


DeploymentConfig = DockerDeploymentConfig | ModalDeploymentConfig
