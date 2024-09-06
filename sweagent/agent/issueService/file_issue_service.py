import logging
from pathlib import Path

from sweagent.utils.log import default_logger
from sweagent.agent.issueService.issue_service import (
    IssueService, 
    ProblemStatementResults, 
    ProblemStatementSource
)

class FileIssueService(IssueService):
    def __init__(self, data_path):
        super().__init__(data_path)

    def _get_problem_statement_results_from_text(self, text: str):
        # self.args["instance_id"] = hashlib.sha256(self.args["problem_statement"].encode()).hexdigest()[:6]
        return ProblemStatementResults(text, ProblemStatementSource.LOCAL)

    def get_problem_statement(self):
        default_logger.debug(f'File {self.data_path}')

        if self.data_path.startswith("text://"):
            results = self._get_problem_statement_results_from_text(self.data_path.removeprefix("text://"))
        elif Path(self.data_path).is_file():
            results = self._get_problem_statement_results_from_text(Path(self.data_path).read_text())
        else:
            raise ValueError(f"Invalid file path: {self.data_path}")

        return results