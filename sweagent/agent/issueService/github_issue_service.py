from __future__ import annotations

from ghapi.all import GhApi

from sweagent.agent.issueService.issue_service import (
    GITHUB_ISSUE_URL_PATTERN,
    IssueService,
    ProblemStatementResults,
    ProblemStatementSource,
)
from sweagent.environment.utils import InvalidGithubURL
from sweagent.utils.config import keys_config


class GitHubIssueService(IssueService):
    def __init__(self, data_path):
        super().__init__(data_path)

        self._github_token: str = keys_config.get("GITHUB_TOKEN", "")  # type: ignore

    def _parse_gh_issue_url(self, issue_url: str) -> tuple[str, str, str]:
        """
        Returns:
            owner: Repo owner
            repo: Repo name
            issue number: Issue number as str

        Raises:
            InvalidGithubURL: If the URL is not a valid github issue URL
        """
        match = GITHUB_ISSUE_URL_PATTERN.search(issue_url)
        if not match:
            msg = f"Invalid GitHub issue URL: {issue_url}"
            raise InvalidGithubURL(msg)
        res = match.groups()
        assert len(res) == 3
        return tuple(res)  # type: ignore

    def _get_problem_statement_from_github_issue(
        self, owner: str, repo: str, issue_number: str, *, token: str | None = ""
    ) -> str:
        """Return problem statement from github issue"""
        api = GhApi(token=token)
        issue = api.issues.get(owner, repo, issue_number)
        title = issue.title if issue.title else ""
        body = issue.body if issue.body else ""
        problem_statement = f"{title}\n{body}\n"
        instance_id = f"{owner}__{repo}-i{issue_number}"
        return ProblemStatementResults(problem_statement, instance_id, ProblemStatementSource.ONLINE)

    def get_problem_statement(self):
        owner, repo, issue_number = self._parse_gh_issue_url(self.data_path)
        return self._get_problem_statement_from_github_issue(
            owner,
            repo,
            issue_number,
            token=self._github_token,
        )
