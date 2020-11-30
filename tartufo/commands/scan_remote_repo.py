from pathlib import Path
from shutil import rmtree
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import click

from tartufo import types, util
from tartufo.scanner import GitRepoScanner, Issue


@click.command("scan-remote-repo")
@click.option("--since-commit", help="Only scan from a given commit hash.")
@click.option(
    "--max-depth",
    default=1000000,
    show_default=True,
    help="The max commit depth to go back when searching for secrets.",
)
@click.option("--branch", help="Specify a branch name to scan only that branch.")
@click.option(
    "-wd",
    "--work-dir",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        allow_dash=False,
        resolve_path=True,
    ),
    help="Specify a working directory; this is where the repository will be cloned "
    "to before scanning.",
)
@click.argument("git-url")
@click.pass_obj
@click.pass_context
def main(
    ctx: click.Context,
    options: types.GlobalOptions,
    git_url: str,
    since_commit: Optional[str],
    max_depth: int,
    branch: Optional[str],
    work_dir: Optional[str],
) -> Tuple[str, List[Issue]]:
    """Automatically clone and scan a remote git repository."""
    git_options = types.GitOptions(
        since_commit=since_commit, max_depth=max_depth, branch=branch, fetch=False
    )
    repo_path: Optional[Path] = None
    if work_dir:
        # Make sure we clone into a sub-directory of the working directory
        #   so that we don't inadvertently delete the working directory
        repo_name = urlparse(git_url).path.split("/")[-1]
        repo_path = Path(work_dir) / repo_name
        repo_path.mkdir(parents=True)
    issues: List[Issue] = []
    try:
        repo_path = util.clone_git_repo(git_url, repo_path)
        scanner = GitRepoScanner(options, git_options, str(repo_path))
        issues = scanner.scan()
    except types.GitException as exc:
        util.fail(f"Error cloning remote repo: {exc}", ctx)
    except types.TartufoException as exc:
        util.fail(str(exc), ctx)
    finally:
        if repo_path and repo_path.exists():
            rmtree(str(repo_path), onerror=util.del_rw)
    return (git_url, issues)
