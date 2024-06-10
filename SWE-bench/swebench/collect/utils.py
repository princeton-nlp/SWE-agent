import logging
import re
import requests
import time

from bs4 import BeautifulSoup
from ghapi.core import GhApi
from fastcore.net import HTTP404NotFoundError, HTTP403ForbiddenError
from typing import Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Repo:
    def __init__(self, owner: str, name: str, token: Optional[str] = None):
        """
        Init to retrieve target repository and create ghapi tool

        Args:
            owner (str): owner of target repository
            name (str): name of target repository
            token (str): github token
        """
        self.owner = owner
        self.name = name
        self.token = token
        self.api = GhApi(token=token)
        self.repo = self.call_api(self.api.repos.get, owner=owner, repo=name)

    def call_api(self, func: callable, **kwargs) -> dict:
        """
        API call wrapper with rate limit handling (checks every 5 minutes if rate limit is reset)

        Args:
            func (callable): API function to call
            **kwargs: keyword arguments to pass to API function
        Return:
            values (dict): response object of `func`
        """
        while True:
            try:
                values = func(**kwargs)
                return values
            except HTTP403ForbiddenError as e:
                while True:
                    rl = self.api.rate_limit.get()
                    logger.info(
                        f"[{self.owner}/{self.name}] Rate limit exceeded, waiting for 5 minutes, remaining: {rl.resources.core.remaining}"
                    )
                    if rl.resources.core.remaining > 0:
                        break
                    time.sleep(60 * 5)
            except HTTP404NotFoundError as e:
                logger.info(f"[{self.owner}/{self.name}] Resource not found {kwargs}")
                return None

    def extract_resolved_issues(self, pull: dict) -> list[str]:
        """
        Extract list of issues referenced by a PR

        Args:
            pull (dict): PR dictionary object from GitHub
        Return:
            resolved_issues (list): list of issue numbers referenced by PR
        """
        # Define 1. issue number regex pattern 2. comment regex pattern 3. keywords
        issues_pat = re.compile(r"(\w+)\s+\#(\d+)")
        comments_pat = re.compile(r"(?s)<!--.*?-->")
        keywords = {
            "close",
            "closes",
            "closed",
            "fix",
            "fixes",
            "fixed",
            "resolve",
            "resolves",
            "resolved",
        }

        # Construct text to search over for issue numbers from PR body and commit messages
        text = pull.title if pull.title else ""
        text += "\n" + (pull.body if pull.body else "")
        commits = self.get_all_loop(
            self.api.pulls.list_commits, pull_number=pull.number, quiet=True
        )
        commit_messages = [commit.commit.message for commit in commits]
        commit_text = "\n".join(commit_messages) if commit_messages else ""
        text += "\n" + commit_text
        # Remove comments from text
        text = comments_pat.sub("", text)
        # Look for issue numbers in text via scraping <keyword, number> patterns
        references = dict(issues_pat.findall(text))
        resolved_issues = list()
        if references:
            for word, issue_num in references.items():
                if word.lower() in keywords:
                    resolved_issues.append(issue_num)
        return resolved_issues

    def get_all_loop(
        self,
        func: callable,
        per_page: int = 100,
        num_pages: Optional[int] = None,
        quiet: bool = False,
        **kwargs,
    ) -> list:
        """
        Return all values from a paginated API endpoint.
        
        Args:
            func (callable): API function to call
            per_page (int): number of values to return per page
            num_pages (int): number of pages to return
            quiet (bool): whether to print progress
            **kwargs: keyword arguments to pass to API function
        """
        page = 1
        args = {
            "owner": self.owner,
            "repo": self.name,
            "per_page": per_page,
            **kwargs,
        }
        while True:
            try:
                # Get values from API call
                values = func(**args, page=page)
                yield from values
                if len(values) == 0:
                    break
                if not quiet:
                    rl = self.api.rate_limit.get()
                    logger.info(
                        f"[{self.owner}/{self.name}] Processed page {page} ({per_page} values per page). Remaining calls: {rl.resources.core.remaining}"
                    )
                if num_pages is not None and page >= num_pages:
                    break
                page += 1
            except Exception as e:
                # Rate limit handling
                logger.error(f"Error processing page {page}: {e}")
                while True:
                    rl = self.api.rate_limit.get()
                    if rl.resources.core.remaining > 0:
                        break
                    logger.info(
                        f"[{self.owner}/{self.name}] Waiting for rate limit reset, checking again in 5 minutes"
                    )
                    time.sleep(60 * 5)
        if not quiet:
            logger.info(
                f"[{self.owner}/{self.name}] Processed {(page-1)*per_page + len(values)} values"
            )

    def get_all_issues(
        self,
        per_page: int = 100,
        num_pages: Optional[int] = None,
        direction: str = "asc",
        sort: str = "created",
        state: str = "closed",
        quiet: bool = False,
    ) -> list:
        """
        Wrapper for API call to get all issues from repo

        Args:
            per_page (int): number of issues to return per page
            num_pages (int): number of pages to return
            direction (str): direction to sort issues
            sort (str): field to sort issues by
            state (str): state of issues to look for
            quiet (bool): whether to print progress
        """
        issues = self.get_all_loop(
            self.api.issues.list_for_repo,
            num_pages=num_pages,
            per_page=per_page,
            direction=direction,
            sort=sort,
            state=state,
            quiet=quiet,
        )
        return issues

    def get_all_pulls(
        self,
        per_page: int = 100,
        num_pages: Optional[int] = None,
        direction: str = "asc",
        sort: str = "created",
        state: str = "closed",
        quiet: str = False,
    ) -> list:
        """
        Wrapper for API call to get all PRs from repo

        Args:
            per_page (int): number of PRs to return per page
            num_pages (int): number of pages to return
            direction (str): direction to sort PRs
            sort (str): field to sort PRs by
            state (str): state of PRs to look for
            quiet (bool): whether to print progress
        """
        pulls = self.get_all_loop(
            self.api.pulls.list,
            num_pages=num_pages,
            direction=direction,
            per_page=per_page,
            sort=sort,
            state=state,
            quiet=quiet,
        )
        return pulls


def extract_problem_statement_and_hints(pull: dict, repo: Repo) -> tuple[str, str]:
    """
    Extract problem statement from issues associated with a pull request

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
    Return:
        text (str): problem statement
        hints (str): hints
    """
    if repo.name == "django":
        return extract_problem_statement_and_hints_django(pull, repo)
    text = ""
    all_hint_texts = list()
    for issue_number in pull["resolved_issues"]:
        issue = repo.call_api(
            repo.api.issues.get,
            owner=repo.owner,
            repo=repo.name,
            issue_number=issue_number,
        )
        if issue is None:
            continue
        title = issue.title if issue.title else ""
        body = issue.body if issue.body else ""
        text += f"{title}\n{body}\n"
        issue_number = issue.number
        hint_texts = _extract_hints(pull, repo, issue_number)
        hint_text = "\n".join(hint_texts)
        all_hint_texts.append(hint_text)
    return text, "\n".join(all_hint_texts) if all_hint_texts else ""


def _extract_hints(pull: dict, repo: Repo, issue_number: int) -> list[str]:
    """
    Extract hints from comments associated with a pull request (before first commit)

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
        issue_number (int): issue number
    Return:
        hints (list): list of hints
    """
    # Get all commits in PR
    commits = repo.get_all_loop(
        repo.api.pulls.list_commits, pull_number=pull["number"], quiet=True
    )
    commits = list(commits)
    if len(commits) == 0:
        # If there are no comments, return no hints
        return []
    # Get time of first commit in PR
    commit_time = commits[0].commit.author.date  # str
    commit_time = time.mktime(time.strptime(commit_time, "%Y-%m-%dT%H:%M:%SZ"))
    # Get all comments in PR
    all_comments = repo.get_all_loop(
        repo.api.issues.list_comments, issue_number=issue_number, quiet=True
    )
    all_comments = list(all_comments)
    # Iterate through all comments, only keep comments created before first commit
    comments = list()
    for comment in all_comments:
        comment_time = time.mktime(
            time.strptime(comment.updated_at, "%Y-%m-%dT%H:%M:%SZ")
        )  # use updated_at instead of created_at
        if comment_time < commit_time:
            comments.append(comment)
        else:
            break
        # only include information available before the first commit was created
    # Keep text from comments
    comments = [comment.body for comment in comments]
    return comments


def extract_patches(pull: dict, repo: Repo) -> tuple[str, str]:
    """
    Get patch and test patch from PR

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
    Return:
        patch_change_str (str): gold patch
        patch_test_str (str): test patch
    """
    # Convert diff to patch format with "index" lines removed
    patch = requests.get(pull["diff_url"]).text
    if patch.endswith("\n"):
        patch = patch[:-1]
    # Create change patch and test patch
    patch_change, patch_test = [], []

    # Flag to determine if current diff block is a test or general change
    # Values: 'test', 'diff', None
    flag = None

    for line in patch.split("\n"):
        # Exclude commit specific metadata
        if line.startswith("index "):
            continue
        # Determine if current diff block is a test or general change
        if line.startswith("diff --git a/"):
            words = set(re.split(r" |_|\/|\.", line.lower()))
            flag = (
                "test"
                if ("test" in words or "tests" in words or "testing" in words)
                else "diff"
            )
            if flag != "test" and not line.strip().endswith(".py"):
                flag = None
        # Append line to separate patch depending on flag status
        if flag == "test":
            patch_test.append(line)
        elif flag == "diff":
            patch_change.append(line)

    patch_change_str = "\n".join(patch_change) + "\n" if len(patch_change) > 0 else ""
    patch_test_str = "\n".join(patch_test) + "\n" if len(patch_test) > 0 else ""
    return patch_change_str, patch_test_str


### MARK: Repo Specific Parsing Functions ###
def extract_problem_statement_and_hints_django(
    pull: dict, repo: Repo
) -> tuple[str, str]:
    """
    Get problem statement and hints from issues associated with a pull request

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
    Return:
        text (str): problem statement
        hints (str): hints
    """
    text = ""
    all_hints_text = list()
    for issue_number in pull["resolved_issues"]:
        url = f"https://code.djangoproject.com/ticket/{issue_number}"
        resp = requests.get(url)
        if resp.status_code != 200:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get problem statement (title + body)
        issue_desc = soup.find("div", {"id": "ticket"})
        title = issue_desc.find("h1", class_="searchable").get_text()
        title = re.sub(r"\s+", " ", title).strip()
        body = issue_desc.find("div", class_="description").get_text()
        body = re.sub(r"\n+", "\n", body)
        body = re.sub(r"    ", "\t", body)
        body = re.sub(r"[ ]{2,}", " ", body).strip()
        text += f"{title}\n{body}\n"

        # Get time of first commit in PR
        commits = repo.get_all_loop(
            repo.api.pulls.list_commits, pull_number=pull["number"], quiet=True
        )
        commits = list(commits)
        if len(commits) == 0:
            continue
        commit_time = commits[0].commit.author.date
        commit_time = time.mktime(time.strptime(commit_time, "%Y-%m-%dT%H:%M:%SZ"))

        # Get all comments before first commit
        comments_html = soup.find("div", {"id": "changelog"})
        div_blocks = comments_html.find_all("div", class_="change")
        comments = []
        # Loop through each div block
        for div_block in div_blocks:
            # Find the comment text and timestamp
            comment_resp = div_block.find("div", class_="comment")
            timestamp_resp = div_block.find("a", class_="timeline")
            if comment_resp is None or timestamp_resp is None:
                continue

            comment_text = re.sub(r"\s+", " ", comment_resp.text).strip()
            timestamp = timestamp_resp["title"]
            if timestamp.startswith("See timeline at "):
                timestamp = timestamp[len("See timeline at ") :]
            timestamp = time.mktime(time.strptime(timestamp, "%m/%d/%y %H:%M:%S"))

            # Append the comment and timestamp as a tuple to the comments list
            if timestamp < commit_time:
                all_hints_text.append((comment_text, timestamp))

    return text, all_hints_text
