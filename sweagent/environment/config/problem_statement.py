import hashlib
import uuid
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from sweagent.utils.config import keys_config
from sweagent.utils.github import _get_problem_statement_from_github_issue, _parse_gh_issue_url
from sweagent.utils.log import get_logger

logger = get_logger("Config", emoji="⚙️")


class ProblemStatement(Protocol):
    """A problem statement for a task."""

    id: str

    def get_problem_statement(self) -> str: ...


class EmptyProblemStatement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["empty"] = "empty"
    """Discriminator for (de)serialization/CLI. Do not change."""

    model_config = ConfigDict(extra="forbid")

    def get_problem_statement(self) -> str:
        return ""


class TextProblemStatement(BaseModel):
    text: str

    type: Literal["text"] = "text"
    """Discriminator for (de)serialization/CLI. Do not change."""

    id: str = None  # type: ignore

    model_config = ConfigDict(extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        if self.id is None:
            logger.info("Setting problem statement id to hash of text")
            self.id = hashlib.sha256(self.text.encode()).hexdigest()[:6]

    def get_problem_statement(self) -> str:
        return self.text


class FileProblemStatement(BaseModel):
    path: Path

    type: Literal["text_file"] = "text_file"
    """Discriminator for (de)serialization/CLI. Do not change."""

    id: str = None  # type: ignore

    model_config = ConfigDict(extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        if self.id is None:
            logger.info("Setting problem statement id to hash of file contents (path: %s)", self.path)
            self.id = hashlib.sha256(self.get_problem_statement().encode()).hexdigest()[:6]

    def get_problem_statement(self) -> str:
        return self.path.read_text()


class GithubIssue(BaseModel):
    url: str

    type: Literal["github"] = "github"
    """Discriminator for (de)serialization/CLI. Do not change."""

    id: str = None  # type: ignore

    model_config = ConfigDict(extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        if self.id is None:
            logger.info("Setting problem statement based on github issue url")
            owner, repo, issue_number = _parse_gh_issue_url(self.url)
            self.id = f"{owner}__{repo}-i{issue_number}"

    def get_problem_statement(self) -> str:
        owner, repo, issue_number = _parse_gh_issue_url(self.url)
        return _get_problem_statement_from_github_issue(
            owner, repo, issue_number, token=keys_config.get("GITHUB_TOKEN")
        )


ProblemStatementConfig = TextProblemStatement | GithubIssue | EmptyProblemStatement | FileProblemStatement
