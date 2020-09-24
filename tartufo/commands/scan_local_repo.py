from typing import List, Optional, Tuple

import click

from tartufo import types, util
from tartufo.scanner import GitRepoScanner, Issue


@click.command("scan-local-repo")
@click.option("--since-commit", help="Only scan from a given commit hash.")
@click.option(
    "--max-depth",
    default=1000000,
    show_default=True,
    help="The max commit depth to go back when searching for secrets.",
)
@click.option("--branch", help="Specify a branch name to scan only that branch.")
@click.argument(
    "repo-path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, allow_dash=False),
)
@click.pass_obj
@click.pass_context
def main(
    ctx: click.Context,
    options: types.GlobalOptions,
    repo_path: str,
    since_commit: Optional[str],
    max_depth: int,
    branch: Optional[str],
) -> Tuple[str, List[Issue]]:
    """Scan a repository already cloned to your local system."""
    git_options = types.GitOptions(
        since_commit=since_commit, max_depth=max_depth, branch=branch
    )
    issues: List[Issue] = []
    try:
        scanner = GitRepoScanner(options, git_options, str(repo_path))
        issues = scanner.scan()
    except types.GitLocalException as exc:
        util.fail(f"{repo_path} is not a valid git repository.", ctx)
    except types.GitRemoteException as exc:
        util.fail(f"There was an error fetching from the remote repository: {exc}", ctx)
    except types.TartufoException as exc:
        util.fail(str(exc), ctx)
    return (str(repo_path), issues)
