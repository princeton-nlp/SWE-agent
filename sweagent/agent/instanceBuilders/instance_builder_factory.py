import re

from abc import ABC, abstractmethod
from enum import Enum, auto
import logging
from sweagent.utils.log import default_logger, get_logger

class InstanceBuilder(ABC):
    def __init__(self, data_path):
        self.data_path = data_path

    @abstractmethod
    def get_instance(self, issue_id):
        pass

    # ... other common methods

class GitHubInstanceBuilder(InstanceBuilder):
    def __init__(self, data_path):
        super().__init__(data_path)

    def get_instance(self):
        default_logger.debug(f'GitHub {self.data_path}')

class JiraInstanceBuilder(InstanceBuilder):
    def __init__(self, data_path):
        super().__init__(data_path)

    def get_instance(self):
        default_logger.debug(f'Jira {self.data_path}')

class FileInstanceBuilder(InstanceBuilder):
    def __init__(self, data_path):
        super().__init__(data_path)

    def get_instance(self):
        default_logger.debug(f'File {self.data_path}')

class IssueDatabaseType(Enum):
    GITHUB = auto()
    JIRA = auto()
    FILE = auto()

class InstanceBuilderFactory:
    GITHUB_ISSUE_URL_PATTERN = re.compile(r"github\.com\/(.*?)\/(.*?)\/issues\/(\d+)")
    JIRA_ISSUE_URL_PATTERN = re.compile(r"atlassian\.net\/browse\/([A-Z]+-\d+)")

    def parse_issue_db_type(self, data_path: str) -> IssueDatabaseType:
        """Parse the data_path and determine what kind of issue repository we're using"""
        if self.GITHUB_ISSUE_URL_PATTERN.search(data_path) is not None:
            return IssueDatabaseType.GITHUB
        
        elif self.JIRA_ISSUE_URL_PATTERN.search(data_path) is not None:
            return IssueDatabaseType.JIRA

        else:
            return IssueDatabaseType.FILE
        

    def create_instance_builder(self, data_path: str):
        issueType = self.parse_issue_db_type(data_path)

        match issueType:
            case IssueDatabaseType.GITHUB:
                return GitHubInstanceBuilder(data_path)
            case IssueDatabaseType.JIRA:
                return JiraInstanceBuilder(data_path)
            case IssueDatabaseType.FILE:
                return FileInstanceBuilder(data_path)
            case _:
                raise ValueError("Invalid Issue Source")

# # In your main application logic
# factory = InstanceBuilderFactory()
# reader = factory.create_issue_reader(user_selected_source)
# issue_details = reader.get_issue_details(issue_id)