from typing import Tuple

import click

from tartufo import types, util
from tartufo.scanner import FolderScanner


@click.command("scan-folder")
@click.option(
    "--include-path-pattern", default="*", help="Glob expression used to filter files."
)
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, allow_dash=False),
)
@click.pass_obj
@click.pass_context
def main(
    ctx: click.Context,
    options: types.GlobalOptions,
    target: str,
    include_path_pattern: str,
) -> Tuple[str, FolderScanner]:
    """Scan a folder."""
    folder_options = types.FolderOptions(
        include_path_pattern=include_path_pattern,
    )
    try:
        scanner = FolderScanner(options, folder_options, target)
        scanner.scan()
    except types.TartufoException as exc:
        util.fail(str(exc), ctx)
    return target, scanner
