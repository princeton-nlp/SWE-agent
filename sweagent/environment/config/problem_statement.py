import hashlib
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from sweagent.utils.config import keys_config
from sweagent.utils.github import _get_problem_statement_from_github_issue, _parse_gh_issue_url


class EmptyProblemStatement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["empty"] = "empty"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def get_problem_statement(self) -> str:
        return ""


class TextProblemStatement(BaseModel):
    problem_statement: str = ""

    type: Literal["text"] = "text"
    """Discriminator for (de)serialization/CLI. Do not change."""

    @property
    def id(self) -> str:
        return hashlib.sha256(self.problem_statement.encode()).hexdigest()[:6]

    def get_problem_statement(self) -> str:
        return self.problem_statement


class FileProblemStatement(BaseModel):
    path: str = ""

    type: Literal["text_file"] = "text_file"
    """Discriminator for (de)serialization/CLI. Do not change."""

    @property
    def id(self) -> str:
        return hashlib.sha256(self.get_problem_statement().encode()).hexdigest()[:6]

    def get_problem_statement(self) -> str:
        return Path(self.path).read_text()


class GithubIssue(BaseModel):
    issue_url: str = ""

    type: Literal["github"] = "github"
    """Discriminator for (de)serialization/CLI. Do not change."""

    @property
    def id(self) -> str:
        org, repo, issue = self.issue_url.split("/")[-3:]
        return f"{org}__{repo}-i{issue}"

    def get_problem_statement(self) -> str:
        owner, repo, issue_number = _parse_gh_issue_url(self.issue_url)
        return _get_problem_statement_from_github_issue(
            owner, repo, issue_number, token=keys_config.get("GITHUB_TOKEN")
        )


ProblemStatementConfig = TextProblemStatement | GithubIssue | EmptyProblemStatement | FileProblemStatement
