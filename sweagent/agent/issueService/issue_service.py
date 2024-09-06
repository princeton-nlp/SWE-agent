from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import Enum

GITHUB_ISSUE_URL_PATTERN = re.compile(r"github\.com\/(.*?)\/(.*?)\/issues\/(\d+)")
JIRA_ISSUE_URL_PATTERN = re.compile(r"atlassian\.net\/browse\/([A-Z]+-\d+)")


class ProblemStatementSource(Enum):
    LOCAL = "local"
    ONLINE = "online"
    SWEBENCH = "swe-bench"


class ProblemStatementResults:
    def __init__(self, problem_statement: str, instance_id: str, problem_statement_source: ProblemStatementSource):
        self.problem_statement = problem_statement
        self.instance_id = instance_id
        self.problem_statement_source = problem_statement_source


class IssueService(ABC):
    def __init__(self, data_path):
        self.data_path = data_path

    @abstractmethod
    def get_problem_statement(self, issue_id) -> ProblemStatementResults:
        pass

    # ... other common methods
