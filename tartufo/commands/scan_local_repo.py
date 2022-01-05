from typing import Optional

import click

from tartufo import types, util
from tartufo.scanner import GitRepoScanner


@click.command("scan-local-repo")
@click.option("--since-commit", help="Only scan from a given commit hash.", hidden=True)
@click.option(
    "--max-depth",
    default=1000000,
    show_default=True,
    help="The max commit depth to go back when searching for secrets.",
    hidden=True,
)
@click.option("--branch", help="Specify a branch name to scan only that branch.")
@click.argument(
    "repo-path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, allow_dash=False),
)
@click.option(
    "--include-submodules/--exclude-submodules",
    is_flag=True,
    default=False,
    show_default=True,
    help="Controls whether the contents of git submodules are scanned",
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
    include_submodules: bool,
) -> GitRepoScanner:
    """Scan a repository already cloned to your local system."""
    git_options = types.GitOptions(
        since_commit=since_commit,
        max_depth=max_depth,
        branch=branch,
        include_submodules=include_submodules,
    )
    scanner = None
    try:
        scanner = GitRepoScanner(options, git_options, str(repo_path))
        util.process_issues(repo_path, scanner, options)
    except types.GitLocalException:
        util.fail(f"{repo_path} is not a valid git repository.", ctx)
    except types.TartufoException as exc:
        util.fail(str(exc), ctx)
    return scanner  # type: ignore
