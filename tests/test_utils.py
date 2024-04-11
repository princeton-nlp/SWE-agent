from sweagent.environment.utils import format_trajectory_markdown, _MARKDOWN_TRAJECTORY_EMOJI_MAPPING, remove_triple_backticks, parse_gh_repo_url, parse_gh_issue_url, is_github_issue_url, get_associated_commit_urls

def test_format_trajectory_markdown(test_trajectory):
    formatted = format_trajectory_markdown(test_trajectory["trajectory"])
    assert formatted.startswith("<details>")
    assert formatted.endswith("</details>")
    for emoji in _MARKDOWN_TRAJECTORY_EMOJI_MAPPING.values():
        assert emoji in formatted


def test_remove_triple_backticks():
    assert remove_triple_backticks("```") == ""


def test_parse_gh_repo_url():
    url = "https://github.com/princeton-nlp/SWE-agent"
    owner, repo = parse_gh_repo_url(url)
    assert owner == "princeton-nlp"
    assert repo == "SWE-agent"


def test_parse_gh_issue_url():
    url = "https://github.com/princeton-nlp/SWE-agent/issues/43"
    owner, repo, no = parse_gh_issue_url(url)
    assert owner == "princeton-nlp"
    assert repo == "SWE-agent"
    assert no == "43"


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