import os
import re
import subprocess
from pathlib import Path

from ..core.config import settings
from ..utils.file_utils import remove_tree

GITHUB_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")


class GithubError(ValueError):
    pass


def parse_github_url(url: str) -> tuple[str, str]:
    m = GITHUB_RE.match(url.strip())
    if not m:
        raise GithubError("Only public https://github.com/<owner>/<repo> URLs are supported")
    return m.group(1), m.group(2)


def validate_branch(branch: str | None) -> str | None:
    if not branch:
        return None
    if not BRANCH_RE.match(branch) or branch.startswith("-") or ".." in branch:
        raise GithubError("Invalid branch name")
    return branch


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file() and not f.is_symlink())


def clone_repo(url: str, dest: Path, branch: str | None = None) -> str:
    """Shallow clone (no code execution, no hooks). Returns commit sha."""
    owner, repo = parse_github_url(url)
    branch = validate_branch(branch)
    remove_tree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "-c", "core.hooksPath=/dev/null", "-c", "protocol.file.allow=never",
           "clone", "--depth", "1", "--single-branch", "--no-tags"]
    if branch:
        cmd += ["--branch", branch]
    cmd += ["--", f"https://github.com/{owner}/{repo}.git", str(dest)]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180, env=env)
    except subprocess.TimeoutExpired as e:
        raise GithubError("Clone timed out (repository too large or network too slow)") from e
    except subprocess.CalledProcessError as e:
        raise GithubError("Clone failed: the repository may be private, or the URL/branch may be wrong") from e
    except FileNotFoundError as e:
        raise GithubError("git is not installed on the server") from e

    sha = ""
    try:
        sha = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=20).stdout.strip()
    except Exception:
        pass
    remove_tree(dest / ".git")
    if _dir_size(dest) > settings.max_repo_mb_clone * 1024 * 1024:
        remove_tree(dest)
        raise GithubError("Repository exceeds the size limit")
    return sha
