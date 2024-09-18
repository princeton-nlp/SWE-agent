from __future__ import annotations

import hashlib
import os
import subprocess

import pytest

from sweagent.environment.utils import (
    InvalidGithubURL,
    format_trajectory_markdown,
    get_associated_commit_urls,
    get_instances,
    is_github_issue_url,
    is_github_repo_url,
    parse_gh_issue_url,
    parse_gh_repo_url,
    remove_triple_backticks,
)

_TOKEN = {"token": os.environ.get("GITHUB_TOKEN", "")}


def test_format_trajectory_markdown(test_trajectory):
    formatted = format_trajectory_markdown(test_trajectory["trajectory"])
    assert formatted.startswith("<details>")
    assert formatted.endswith("</details>")


def test_remove_triple_backticks():
    assert remove_triple_backticks("```") == ""


def test_is_github_repo_url():
    assert is_github_repo_url("https://github.com/princeton-nlp/SWE-agent")
    assert is_github_repo_url("https://github.com/princeton-nlp/SWE-agent/anything")
    assert is_github_repo_url("github.com/princeton-nlp/SWE-agent/anything")
    assert not is_github_repo_url("")
    assert not is_github_repo_url("/path/to/file")


def test_parse_gh_repo_url():
    assert parse_gh_repo_url("https://github.com/princeton-nlp/SWE-agent") == ("princeton-nlp", "SWE-agent")
    assert parse_gh_repo_url("github.com/princeton-nlp/SWE-agent") == ("princeton-nlp", "SWE-agent")
    assert parse_gh_repo_url("github.com/princeton-nlp/SWE-agent/asdfjsdfg") == ("princeton-nlp", "SWE-agent")
    assert parse_gh_repo_url("git@github.com/princeton-nlp/SWE-agent/asdfjsdfg") == ("princeton-nlp", "SWE-agent")


def test_parse_gh_repo_url_fails():
    with pytest.raises(InvalidGithubURL):
        parse_gh_repo_url("adfkj;lasdfl;kj")
    with pytest.raises(InvalidGithubURL):
        parse_gh_repo_url("github.com/")
    with pytest.raises(InvalidGithubURL):
        parse_gh_repo_url("github.com//a/")


def test_parse_gh_issue_url():
    url = "https://github.com/princeton-nlp/SWE-agent/issues/43"
    owner, repo, no = parse_gh_issue_url(url)
    assert owner == "princeton-nlp"
    assert repo == "SWE-agent"
    assert no == "43"


def test_parse_gh_issue_url_fails():
    with pytest.raises(InvalidGithubURL):
        parse_gh_issue_url("https://github.com/a/b")
    with pytest.raises(InvalidGithubURL):
        parse_gh_issue_url("https://github.com/a/b////")


def test_is_from_github_url():
    assert not is_github_issue_url("")
    assert is_github_issue_url("https://github.com/princeton-nlp/SWE-agent/issues/43")


def test_get_associated_commit_urls():
    assoc = get_associated_commit_urls(
        org="princeton-nlp",
        repo="SWE-agent",
        issue_number="41",
        token=os.environ.get("GITHUB_TOKEN", ""),
    )
    assert len(assoc) > 0


def test_get_instance_gh_issue():
    instance = get_instances("https://github.com/swe-agent/test-repo/issues/1", **_TOKEN)[0]
    compare_with = {
        "repo": "swe-agent/test-repo",
        "instance_id": "swe-agent__test-repo-i1",
        "repo_type": "github",
    }
    for key in compare_with:
        assert instance[key] == compare_with[key]
    assert "SyntaxError" in instance["problem_statement"]
    assert len(instance["base_commit"]) > 10
    assert instance["version"]


def clone_repo(tmp_path, repo_url):
    cmd = [
        "git",
        "clone",
        repo_url,
    ]
    subprocess.run(cmd, check=True, cwd=tmp_path)


def test_get_instance_gh_issue_local_repo(tmp_path):
    clone_repo(tmp_path, "https://github.com/swe-agent/test-repo/")
    instance = get_instances(
        file_path="https://github.com/swe-agent/test-repo/issues/1",
        repo_path=str(tmp_path / "test-repo"),
        **_TOKEN,
    )[0]
    compare_with = {
        "repo": str(tmp_path.resolve() / "test-repo"),
        "repo_type": "local",
        "instance_id": "swe-agent__test-repo-i1",
    }
    for key in compare_with:
        assert instance[key] == compare_with[key]
    assert "SyntaxError" in instance["problem_statement"]
    assert len(instance["base_commit"]) > 10
    assert instance["version"]


def test_get_instance_local_issue_local_repo(tmp_path):
    clone_repo(tmp_path, "https://github.com/swe-agent/test-repo/")
    issue_path = tmp_path / "issue.txt"
    issue_path.write_text("asdf")
    instance = get_instances(
        file_path=str(issue_path),
        repo_path=str(tmp_path / "test-repo"),
    )[0]
    compare_with = {
        "repo": str(tmp_path.resolve() / "test-repo"),
        "repo_type": "local",
        "instance_id": hashlib.sha256(b"asdf").hexdigest()[:6],
        "problem_statement": "asdf",
    }
    for key in compare_with:
        assert instance[key] == compare_with[key]
    assert len(instance["base_commit"]) > 10
    assert instance["version"]


def test_get_instance_gh_issue_gh_repo(tmp_path):
    instance = get_instances(
        file_path="https://github.com/swe-agent/test-repo/issues/1",
        repo_path="https://github.com/princeton-nlp/SWE-agent",
        **_TOKEN,
    )[0]
    compare_with = {
        "repo": "princeton-nlp/SWE-agent",
        "repo_type": "github",
        "instance_id": "swe-agent__test-repo-i1",
    }
    for key in compare_with:
        assert instance[key] == compare_with[key]
    assert "SyntaxError" in instance["problem_statement"]
    assert len(instance["base_commit"]) > 10
    assert instance["version"]


def test_get_instance_text_issue_gh_repo(tmp_path):
    instance = get_instances(
        file_path="text://this is a test",
        repo_path="https://github.com/princeton-nlp/SWE-agent",
        **_TOKEN,
    )[0]
    compare_with = {
        "repo": "princeton-nlp/SWE-agent",
        "repo_type": "github",
        "problem_statement": "this is a test",
    }
    for key in compare_with:
        assert instance[key] == compare_with[key]
    assert len(instance["base_commit"]) > 10
    assert instance["version"]


def test_load_instances(test_data_path, caplog):
    test_data_sources = test_data_path / "data_sources"
    examples = [example for example in test_data_sources.iterdir() if example.is_file()]
    for example in examples:
        get_instances(file_path=str(example), **_TOKEN)


def test_load_ctf_instances(test_data_path, caplog):
    test_data_sources = test_data_path / "data_sources" / "ctf"
    examples = list(test_data_sources.glob("**/challenge.json"))
    for example in examples:
        get_instances(file_path=str(example), repo_path=str(example.parent))