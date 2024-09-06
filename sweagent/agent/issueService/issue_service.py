import re
from abc import ABC, abstractmethod

GITHUB_ISSUE_URL_PATTERN = re.compile(r"github\.com\/(.*?)\/(.*?)\/issues\/(\d+)")
JIRA_ISSUE_URL_PATTERN = re.compile(r"atlassian\.net\/browse\/([A-Z]+-\d+)")

class IssueService(ABC):
    def __init__(self, data_path):
        self.data_path = data_path

    @abstractmethod
    def get_problem_statement(self, issue_id):
        pass

    # ... other common methods