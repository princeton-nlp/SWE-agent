import re
import requests

from unidiff import PatchSet


def contains_git_commit_hash(text: str) -> bool:
    """
    Returns True if the text contains a git commit hash (40 character SHA-1 hash).
    * Excludes commit hashes that are part of a URL.
    """
    pattern_git_commit_hash = re.compile(r'(?<!/)\b[0-9a-f]{40}\b')
    if re.search(pattern_git_commit_hash, text) is not None:
        return True
    pattern_django_commit_hash = re.compile(r'\[[0-9a-f]{23}\]')
    if re.search(pattern_django_commit_hash, text) is not None:
        return True
    return False


def contains_hyperlinks(text: str, repo: str = None) -> bool:
    """
    Returns True if the text contains a URL. Excludes URLs that are part of the repository.
    """
    if repo:
        repo_prefix = f"http://github.com/{repo}"
        pattern_repo = re.escape(repo_prefix)
        # Adding a negative lookahead assertion to ensure URLs starting with the repository prefix are excluded
        pattern_urls = r'(?:https?://(?!{}).+)|(?:www\.(?!{}).+)'.format(pattern_repo, pattern_repo)
    else:
        pattern_urls = r'https?://(?:www\.)?\S+'

    return bool(re.search(pattern_urls, text))


def contains_image(text: str) -> bool:
    """
    Returns True if the text contains an image or video file extension.
    """
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.svg', '.webp', '.ico', '.heif', '.bpg', '.avif']
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.mpeg']

    pattern_image = '|'.join(re.escape(ext) for ext in image_extensions)
    pattern_video = '|'.join(re.escape(ext) for ext in video_extensions)

    image_regex = re.compile(r'\b({})\b'.format(pattern_image), flags=re.IGNORECASE)
    video_regex = re.compile(r'\b({})\b'.format(pattern_video), flags=re.IGNORECASE)

    return image_regex.search(text) is not None or video_regex.search(text) is not None


def contains_issue_reference(text: str, repo: str) -> bool:
    """
    Returns True if text (problem statement) contains a reference to another issue (e.g. #1234).
    """
    # Look for GitHub style issue references
    pattern_issue_ref = re.compile(r"(\w+)\s+\#(\d+)")
    keywords = {
        "close", "closes", "closed",
        "fix", "fixes", "fixed",
        "resolve", "resolves", "resolved",
    }
    references = dict(pattern_issue_ref.findall(text))
    if references:
        for word, _ in references.items():
            if word.lower() in keywords:
                return True
    
    # Look for GitLab style issue references
    pattern_gitlab = re.compile(r"https?:\/\/gitlab.com\/(.*)\/issues")
    if re.search(pattern_gitlab, text):
        return True

    # Look for GitHub `#` style references + verify if the issue exists
    pattern_issue_ref = re.compile(r'#\d+')
    matches = pattern_issue_ref.findall(text)
    for match in matches:
        url = f"http://github.com/{repo}/issues/{match[1:]}"
        if repo == "django/django":
            url = f"https://code.djangoproject.com/ticket/{match[1:]}"
        if requests.get(url).status_code == 200:
            return True

    return False


def contains_non_modified_files(patch_text: str) -> bool:
    """
    Returns True if the patch contains files that are not modified.
    """
    patch = PatchSet(patch_text)
    return len(patch.removed_files) > 0 or len(patch.added_files) > 0


def contains_pytest_match_arg(patch_test_text: str) -> bool:
    """
    Returns True if the test patch contains a pytest.raises() call with a match argument.
    """
    if any([x in patch_test_text for x in [
        'pytest.raises',
        'pytest.warns',
        'pytest.deprecated_call',
        ]]):
        return 'match' in patch_test_text
    # Django style assertions:
    if any([x in patch_test_text for x in [
        'assertOutput',
        'assertRaises',
        'checks.Error',
        ]]):
        return True
    return False


def leq_n_code_lines(patch_text: str, n: int = 25) -> bool:
    """
    Returns True if the patch has at most n lines of code changed.
    """
    lines = 0
    patch = PatchSet(patch_text)
    for file in patch:
        for hunk in file:
            lines += hunk.added
            lines += hunk.removed
    return lines <= n


def leq_n_files(patch_text: str, n: int = 1) -> bool:
    """
    Returns True if the patch has at most n files.
    """
    patch = PatchSet(patch_text)
    return len(patch.modified_files) <= n


def leq_n_hunks(patch_text: str, n: int = 3) -> bool:
    """
    Returns True if the patch has at most n hunks.
    """
    patch = PatchSet(patch_text)
    num_hunks = sum([
        len([h for h in f])
        for f in patch.modified_files
    ])
    return num_hunks <= n and num_hunks > 0


def leq_n_words(text: str, n: int = 50) -> bool:
    """
    Returns True if the text has at most n words.
    """
    return len(text.split()) <= n
