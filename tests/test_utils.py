import pytest
from sweagent.environment.utils import InvalidGithubURL, format_trajectory_markdown, _MARKDOWN_TRAJECTORY_EMOJI_MAPPING, get_instance_from_github_url, get_instances, is_github_repo_url, remove_triple_backticks, parse_gh_repo_url, parse_gh_issue_url, is_github_issue_url, get_associated_commit_urls

def test_format_trajectory_markdown(test_trajectory):
    formatted = format_trajectory_markdown(test_trajectory["trajectory"])
    assert formatted.startswith("<details>")
    assert formatted.endswith("</details>")
    for emoji in _MARKDOWN_TRAJECTORY_EMOJI_MAPPING.values():
        assert emoji in formatted


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
        issue_number="41"
    )
    assert len(assoc) > 0


def test_get_instance_from_github_url_github_issue():
    instance = get_instances("https://github.com/klieret/swe-agent-test-repo/issues/1")[0]
    compare_with = {
        'repo': 'klieret/swe-agent-test-repo',
        'instance_id': 'klieret__swe-agent-test-repo-i1'
    }
    for key in compare_with:
        assert instance[key] == compare_with[key]
    assert "SyntaxError" in instance["problem_statement"]
    assert len(instance["base_commit"]) > 10
    assert instance["version"]



def test_get_instance_from_github_url_github_issue_overrides():
    instance = get_instances("https://github.com/klieret/swe-agent-test-repo/issues/1", problem_statement="asdf", base_commit="1234")[0]
    assert instance["problem_statement"] == "asdf"
    assert instance["base_commit"] == "1234"


def test_get_instance_from_github_url_github_repo_missing_problem():
    with pytest.raises(ValueError, match=".*Problem statement.*"):
        get_instance_from_github_url("https://github.com/klieret/swe-agent-test-repo/")


def test_get_instance_from_github_url_github_repo():
    instance = get_instance_from_github_url("https://github.com/klieret/swe-agent-test-repo/", problem_statement="asdf")
    assert instance["problem_statement"] == "asdf"
