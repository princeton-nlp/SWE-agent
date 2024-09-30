from __future__ import annotations

import hashlib
from pathlib import Path

from sweagent.agent.issueService.helpers import get_problem_statement_from_challenge_json

from sweagent.agent.issueService.issue_service import IssueService, ProblemStatementResults, ProblemStatementSource
from sweagent.utils.log import default_logger


class ChallengeIssueService(IssueService):
    def __init__(self, data_path):
        super().__init__(data_path)
    
    def _get_challenge_data_from_challenge_json(file_path: str) -> ProblemStatementResults :
        challenge_data = get_problem_statement_from_challenge_json(file_path=file_path)
        
        # todo null checking?
        problem_statement= f"{challenge.name} {challenge.description}"
        instance_id = (
            # sanitize 'name' to only alphanumeric characters
            challenge.get("category", "misc") + "_" + "".join(a for a in challenge_data.name if a.isalnum())
        )

        return ProblemStatementResults(problem_statement, instance_id, ProblemStatementSource.LOCAL)
    
    def get_problem_statement(self) -> ProblemStatementResults:
        default_logger.debug(f"File {self.data_path}")

        return self._get_challenge_data_from_challenge_json(self.data_path)
