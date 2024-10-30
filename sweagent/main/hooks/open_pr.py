from pathlib import Path
from typing import Any

from run import ScriptArguments, logger
from sweagent.agent.agents import Agent
from sweagent.environment.swe_env import SWEEnv
from sweagent.environment.utils import InvalidGithubURL
from sweagent.main.hooks.abstract import MainHook
from sweagent.utils._github import get_associated_commit_urls, get_gh_issue_data, parse_gh_issue_url

# todo: Move this to run.py
# def open_pr(self, *, trajectory, _dry_run: bool = False) -> None:
#     """Create PR to repository

#     Args:
#         trajectory: Trajectory of actions taken by the agent
#         _dry_run: Whether to actually push anything or just simulate it
#     """
#     self.logger.info("Opening PR")
#     # TODO: have better way of handling this
#     # Adding random string suffix to avoid name conflicts if we had a previously failed run
#     issue_url = self.args.data_path
#     try:
#         issue = get_gh_issue_data(issue_url, token=self._github_token)
#     except InvalidGithubURL as e:
#         msg = "Data path must be a github issue URL if --open_pr is set."
#         raise ValueError(msg) from e
#     branch_name = f"swe-agent-fix-#{issue.number}-" + str(random.random())[2:10]

#     self.communicate_with_handling(
#         input="rm -f model.patch",
#         error_msg="Failed to remove model patch",
#         timeout_duration=10,
#     )
#     self.communicate_with_handling(
#         input=f"git checkout -b {branch_name}",
#         error_msg="Failed to switch to new branch",
#         timeout_duration=10,
#     )
#     self.communicate_with_handling(
#         input="git add .",
#         error_msg="Failed to add commits",
#         timeout_duration=10,
#     )
#     dry_run_flag = "--allow-empty" if _dry_run else ""
#     commit_msg = [
#         shlex.quote("Fix: {issue.title}"),
#         shlex.quote("Closes #{issue.number}"),
#     ]
#     self.communicate_with_handling(
#         input=f"git commit -m {commit_msg[0]} -m  {commit_msg[1]} {dry_run_flag}",
#         error_msg="Failed to commit changes",
#         timeout_duration=10,
#     )

#     owner, repo, _ = parse_gh_issue_url(issue_url)
#     # If `--repo_path` was specified with a different github URL, then the record will contain
#     # the forking user
#     assert self.record is not None
#     if self.record["repo_type"] != "github":
#         # We already validated that `--data_path` is a github issue URL
#         # so this is the only case where we can reach here
#         msg = "--repo_path must point to a github URL if --open_pr is set"
#         raise ValueError(msg)
#     forker, _ = self.record["repo"].split("/")
#     head = branch_name
#     remote = "origin"
#     if forker != owner:
#         head = f"{forker}:{branch_name}"
#         token_prefix = ""
#         if self._github_token:
#             token_prefix = f"{self._github_token}@"
#         fork_url = f"https://{token_prefix}github.com/{forker}/{repo}.git"
#         self.logger.debug(f"Using fork: {fork_url}")
#         self.communicate_with_handling(
#             input=f"git remote add fork {fork_url}",
#             error_msg="Failed to create new git remote",
#             timeout_duration=10,
#         )
#         remote = "fork"
#     dry_run_prefix = "echo " if _dry_run else ""
#     self.communicate_with_handling(
#         input=f"{dry_run_prefix} git push {remote} {branch_name}",
#         error_msg=(
#             "Failed to push branch to remote. Please check your token and permissions. "
#             "You might want to push to a fork with the push_gh_repo_url option."
#         ),
#         timeout_duration=10,
#     )
#     body = (
#         f"This is a PR opened by AI tool [SWE Agent](https://github.com/princeton-nlp/SWE-agent/) "
#         f"to close [#{issue.number}]({issue_url}) ({issue.title}).\n\nCloses #{issue.number}."
#     )
#     body += "\n\n" + format_trajectory_markdown(trajectory)
#     api = GhApi(token=self._github_token)
#     if not _dry_run:
#         pr_info = api.pulls.create(  # type: ignore
#             owner=owner,
#             repo=repo,
#             title=f"SWE-agent[bot] PR to fix: {issue.title}",
#             head=head,
#             base="main",
#             body=body,
#             draft=True,
#         )
#         self.logger.info(
#             f"🎉 PR created as a draft at {pr_info.html_url}. Please review it carefully, push "
#             "any required changes onto the branch and then click "
#             "'Ready for Review' to bring it to the attention of the maintainers.",
#         )


class OpenPRHook(MainHook):
    """This hook opens a PR if the issue is solved and the user has enabled the option."""

    def on_init(self, *, args: ScriptArguments, agent: Agent, env: SWEEnv, traj_dir: Path):
        self._env = env
        self._token: str = env._github_token
        self._data_path = args.environment.data_path
        self._open_pr = args.actions.open_pr
        self._skip_if_commits_reference_issue = args.actions.skip_if_commits_reference_issue

    def on_instance_completed(self, *, info, trajectory):
        if self._open_pr and self.should_open_pr(info):
            self._env.open_pr(trajectory=trajectory)

    def should_open_pr(self, info: dict[str, Any]) -> bool:
        """Does opening a PR make sense?"""
        if not info.get("submission"):
            logger.info("Not opening PR because no submission was made.")
            return False
        if info["exit_status"] != "submitted":
            logger.info("Not opening PR because exit status was %s and not submitted.", info["exit_status"])
            return False
        try:
            issue = get_gh_issue_data(self._data_path, token=self._token)
        except InvalidGithubURL:
            logger.info("Currently only GitHub is supported to open PRs to. Skipping PR creation.")
            return False
        if issue.state != "open":
            logger.info(f"Issue is not open (state={issue.state}. Skipping PR creation.")
            return False
        if issue.assignee:
            logger.info("Issue is already assigned. Skipping PR creation. Be nice :)")
            return False
        if issue.locked:
            logger.info("Issue is locked. Skipping PR creation.")
            return False
        org, repo, issue_number = parse_gh_issue_url(self._data_path)
        associated_commits = get_associated_commit_urls(org, repo, issue_number, token=self._token)
        if associated_commits:
            commit_url_strs = ", ".join(associated_commits)
            if self._skip_if_commits_reference_issue:
                logger.info(f"Issue already has associated commits (see {commit_url_strs}). Skipping PR creation.")
                return False
            else:
                logger.warning(
                    "Proceeding with PR creation even though there are already commits "
                    f"({commit_url_strs}) associated with the issue. Please only do this for your own repositories "
                    "or after verifying that the existing commits do not fix the issue.",
                )
        return True


def _remove_triple_backticks(text: str) -> str:
    return "\n".join(line.removeprefix("```") for line in text.splitlines())


def format_trajectory_markdown(trajectory: list[dict[str, str]]):
    """Format a trajectory as a markdown string for use in gh PR description."""
    prefix = [
        "<details>",
        "<summary>Thought process ('trajectory') of SWE-agent (click to expand)</summary>",
        "",
        "",
    ]
    steps = []
    for i, step in enumerate(trajectory):
        step_strs = [
            f"**🧑‍🚒 Response ({i})**: ",
            f"{step['response'].strip()}",
            f"**👀‍ Observation ({i})**:",
            "```",
            f"{_remove_triple_backticks(step['observation']).strip()}",
            "```",
        ]
        steps.append("\n".join(step_strs))
    suffix = [
        "",
        "</details>",
    ]
    return "\n".join(prefix) + "\n\n---\n\n".join(steps) + "\n".join(suffix)
