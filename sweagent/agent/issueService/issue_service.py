from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import Enum

GITHUB_ISSUE_URL_PATTERN = re.compile(r"github\.com\/(.*?)\/(.*?)\/issues\/(\d+)")


class ProblemStatementSource(Enum):
    LOCAL = "local"
    ONLINE = "online"
    SWEBENCH = "swe-bench"


class CtfChallengesCategories(Enum):
    REV = "reverse engineering"
    PWN = "binary exploitation"
    WEB = "web security"
    CRYPTO = "cryptography"
    MISC = "miscellaneous"
    FORENSICS = "forensics"


class ProblemStatementResults:
    def __init__(self, problem_statement: str, instance_id: str, problem_statement_source: ProblemStatementSource):
        self.problem_statement = problem_statement
        self.instance_id = instance_id
        self.problem_statement_source = problem_statement_source


# TODO Put this class somewhere it makes more sense
class ChallengeData:
    def __init__(
        self,
        challenge: object,
        name: str,
        description: str,
        files: list,
        points: int = 10,
        docker_compose: str | None = None,
        port: int | None = None,
        server_name: str = "",
        file_path: str = "",
    ):
        self.challenge = challenge
        self.name = name
        self.description = description
        self.files = files
        self.points = points
        self.docker_compose = docker_compose
        self.port = port
        self.server_name = server_name
        self.file_path = file_path
        self.category_enum = CtfChallengesCategories[challenge["category"].upper()]
        self.category_code_raw = challenge["category"]
        self.category_friendly = self.category_enum.value


class IssueService(ABC):
    def __init__(self, data_path):
        self.data_path = data_path

    @abstractmethod
    def get_problem_statement(self, issue_id) -> ProblemStatementResults:
        pass

    # ... other common methods
