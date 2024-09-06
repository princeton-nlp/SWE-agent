from __future__ import annotations

from enum import Enum, auto

from sweagent.agent.issueService.file_issue_service import FileIssueService
from sweagent.agent.issueService.github_issue_service import GitHubIssueService
from sweagent.agent.issueService.issue_service import GITHUB_ISSUE_URL_PATTERN, JIRA_ISSUE_URL_PATTERN, IssueService
from sweagent.utils.log import default_logger


class JiraIssueService(IssueService):
    def __init__(self, data_path):
        super().__init__(data_path)

    def get_problem_statement(self):
        default_logger.debug(f"Jira {self.data_path}")


class IssueDatabaseType(Enum):
    GITHUB = auto()
    JIRA = auto()
    FILE = auto()


class IssueServiceFactory:
    def _parse_issue_db_type(self, data_path: str) -> IssueDatabaseType:
        """Parse the data_path and determine what kind of issue repository we're using"""
        if GITHUB_ISSUE_URL_PATTERN.search(data_path) is not None:
            return IssueDatabaseType.GITHUB

        elif JIRA_ISSUE_URL_PATTERN.search(data_path) is not None:
            return IssueDatabaseType.JIRA

        else:
            return IssueDatabaseType.FILE

    def create_issue_factory(self, data_path: str):
        issue_type = self._parse_issue_db_type(data_path)

        if issue_type == IssueDatabaseType.GITHUB:
            return GitHubIssueService(data_path)
        elif issue_type == IssueDatabaseType.JIRA:
            return JiraIssueService(data_path)
        elif issue_type == IssueDatabaseType.FILE:
            return FileIssueService(data_path)
        else:
            error_message = "Invalid Issue Source"
            raise ValueError(error_message)
