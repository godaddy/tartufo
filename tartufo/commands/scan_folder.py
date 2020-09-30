from typing import Tuple

import click

from tartufo import types, util
from tartufo.scanner import FolderScanner


@click.command("scan-folder")
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, allow_dash=False),
)
@click.pass_obj
@click.pass_context
def main(
    ctx: click.Context, options: types.GlobalOptions, target: str
) -> Tuple[str, FolderScanner]:
    """Scan a folder."""
    try:
        scanner = FolderScanner(options, target)
        scanner.scan()
    except types.TartufoException as exc:
        util.fail(str(exc), ctx)
    return target, scanner
