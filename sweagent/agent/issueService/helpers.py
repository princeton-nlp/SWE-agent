from __future__ import annotations

import json
from pathlib import Path

from sweagent.agent.issueService.issue_service import ChallengeData


def get_problem_statement_from_challenge_json(file_path: str) -> ChallengeData:
    """For CTF challenges"""
    challenge = json.loads(Path(file_path).read_text())

    # Create a ChallengeData instance
    return ChallengeData(
        challenge=challenge,
        name=challenge["name"],
        description=challenge["description"],
        files=challenge.get("files", []),
        points=challenge.get("points", 10),
        docker_compose=(Path(file_path).parent / "docker-compose.yml")
        if (Path(file_path).parent / "docker-compose.yml").is_file()
        else None,
        port=challenge.get("internal_port") or challenge.get("port"),
        server_name=challenge.get("box", "") if "box" in challenge else "",
        file_path=file_path
    )
