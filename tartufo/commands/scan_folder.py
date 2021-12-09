import sys

import click

from tartufo import types, util
from tartufo.scanner import FolderScanner


@click.command("scan-folder")
@click.option(
    "--recurse/--no-recurse",
    is_flag=True,
    default=True,
    show_default=True,
    help="Recurse and scan the entire folder",
)
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, allow_dash=False),
)
@click.pass_obj
@click.pass_context
def main(
    ctx: click.Context, options: types.GlobalOptions, target: str, recurse: bool
) -> FolderScanner:
    """Scan a folder."""
    try:
        resume: bool = True
        if util.path_contains_git(target) is True:
            resume = click.confirm(
                "This folder is a git repository, and should be scanned using the "
                "scan-local-repo command. Are you sure you wish to proceed?"
            )
        if resume is False:
            sys.exit(0)
        scanner = FolderScanner(options, target, recurse)
        util.process_issues(target, scanner, options)
    except types.TartufoException as exc:
        util.fail(str(exc), ctx)
    return scanner  # type: ignore
