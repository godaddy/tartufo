import pathlib
import shutil
from typing import List, Optional, Tuple

import click
from git.exc import GitCommandError

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
) -> Tuple[str, List[Issue]]:
    """Automatically clone and scan a remote git repository."""
    git_options = types.GitOptions(
        since_commit=since_commit, max_depth=max_depth, branch=branch
    )
    repo_path = None
    issues: List[Issue] = []
    try:
        repo_path = util.clone_git_repo(git_url)
        scanner = GitRepoScanner(options, git_options, str(repo_path))
        issues = scanner.scan()
    except GitCommandError as exc:
        util.fail("Error cloning remote repo: {}".format(exc.stderr.strip()), ctx)
    except types.TartufoScanException as exc:
        util.fail(str(exc), ctx)
    finally:
        if repo_path and pathlib.Path(repo_path).exists():
            shutil.rmtree(repo_path, onerror=util.del_rw)
    return (git_url, issues)
