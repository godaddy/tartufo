from typing import List, Optional, Tuple

import click

from tartufo import types, util
from tartufo.scanner import FolderScanner, Issue


@click.command("scan-folder")
@click.option("--pattern", default="*", help="Glob expression used to filter files.")
@click.argument(
    "folder-path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, allow_dash=False),
)
@click.pass_obj
@click.pass_context
def main(
    ctx: click.Context,
    options: types.GlobalOptions,
    folder_path: str,
    pattern: Optional[str],
) -> Tuple[str, List[Issue]]:
    """Scan a folder."""
    folder_options = types.FolderOptions(pattern=pattern,)
    issues: List[Issue] = []
    try:
        scanner = FolderScanner(options, folder_options, folder_path)
        issues = scanner.scan()
    except types.TartufoException as exc:
        util.fail(str(exc), ctx)
    return str(folder_path), issues
