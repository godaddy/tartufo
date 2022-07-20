import contextlib
import functools
import io
import pathlib
import re
from typing import (
    Any,
    MutableMapping,
    MutableSet,
    Optional,
    Sequence,
    Tuple,
)

import click
import tomlkit

from tartufo import types, util
from tartufo.config import load_config_from_path
from tartufo.scanner import GitRepoScanner

DeprecationSetT = MutableSet[Sequence[str]]


def scan_local_repo(
    options: types.GlobalOptions,
    repo_path: str,
    since_commit: Optional[str],
    max_depth: int,
    branch: Optional[str],
    include_submodules: bool,
) -> Tuple[Optional[GitRepoScanner], io.StringIO]:
    """A reworked version of the scan-local-repo command.

    :param options: The options provided to the top-level tartufo command
    :param repo_path: The local filesystem path pointing to the repository
    :param since_commit: A commit hash to treat as a starting point in history for the scan
    :param max_depth: A maximum depth, or maximum number of commits back in history, to scan
    :param branch: A specific branch to scan
    :param include_submodules: Whether to also scan submodules of the repository
    :returns: A tuple containing optional scanner, and stderr from the scan
    """
    stdout = io.StringIO()
    stderr = io.StringIO()
    scanner = None

    git_options = types.GitOptions(
        since_commit=since_commit,
        max_depth=max_depth,
        branch=branch,
        include_submodules=include_submodules,
    )

    with contextlib.redirect_stdout(stdout):
        with contextlib.redirect_stderr(stderr):
            try:
                scanner = GitRepoScanner(options, git_options, str(repo_path))
                util.process_issues(repo_path, scanner, options)
            except types.GitLocalException:
                message = f"{repo_path} is not a valid git repository."
                click.echo(util.style_error(message), err=True)
            except types.TartufoException as exc:
                click.echo(util.style_error(str(exc)), err=True)

    del stdout
    return scanner, stderr


def get_deprecations(stderr: io.StringIO) -> DeprecationSetT:
    """Finds the deprecated signatures from the given input.

    :param stderr: Stderr output from the scan-local-repo subcommand
    :returns: A set of tuples each containing the old and new signature
    """
    deprecations: DeprecationSetT = set()
    deprecation_rgx = re.compile(
        r"DeprecationWarning: Signature (\w+) was.*use signature (\w+) instead\."
    )

    # Start at the beginning of the buffer
    stderr.seek(0)
    for line in stderr:
        match = deprecation_rgx.search(line)

        if match:
            # This line had a deprecation warning
            deprecations.add(match.groups())

    return deprecations


def replace_deprecated_signatures(
    deprecations: DeprecationSetT, config_data: MutableMapping[str, Any]
) -> int:
    """Update the old deprecated signatures with the new signatures.

    :param deprecations: The deprecated, and replacement signatures
    :param config_data: The current tartufo config data
    :returns: The number of items replaced in config_data
    """
    updated = 0

    for old_sig, new_sig in deprecations:
        targets = functools.partial(lambda o, s: o == s["signature"], old_sig)
        # Iterate all the deprecations and update them everywhere
        # they are found in the exclude-signatures section of config
        for target_signature in filter(targets, config_data["exclude_signatures"]):
            updated += 1
            click.echo(f"{updated}) {old_sig!r} -> {new_sig!r}")
            target_signature["signature"] = new_sig

    return updated


def write_updated_signatures(
    config_path: pathlib.Path, config_data: MutableMapping[str, Any]
) -> None:
    """Read the current config file and update it with the new data.

    :param config_path: The path to the tartufo config file
    :param config_data: The updated config data
    """
    with open(str(config_path), "r") as file:
        result = tomlkit.loads(file.read())

    # Assign the new signatures and write it to the config
    result["tool"]["tartufo"]["exclude-signatures"] = config_data[  # type: ignore
        "exclude_signatures"
    ]

    with open(str(config_path), "w") as file:
        file.write(tomlkit.dumps(result))


def remove_duplicated_entries(config_data: MutableMapping[str, Any]) -> int:
    """Removed any duplicated signature entries in the config.
    Keeps the first instance of each duplicate.

    :param config_data: The config data to check for duplicates
    """
    seen = set()
    count = 0

    for i, exclude in enumerate(config_data["exclude_signatures"].copy()):
        if exclude["signature"] in seen:
            # Remove this duplicated signature
            del config_data["exclude_signatures"][i]
            count += 1
        else:
            # Mark this signature as seen
            seen.add(exclude["signature"])

    return count


@click.command("update-signatures")
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
@click.option(
    "--update-configuration/--no-update-configuration",
    is_flag=True,
    default=True,
    show_default=True,
    help="Whether or not to overwrite the tartufo config file.",
)
@click.option(
    "--remove-duplicates/--no-remove-duplicates",
    is_flag=True,
    default=True,
    show_default=True,
    help="Whether or not to remove duplicated signatures.",
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
    update_configuration: bool,
    remove_duplicates: bool,
) -> GitRepoScanner:
    """Update deprecated signatures for a local repository."""
    config_path, config_data = load_config_from_path(pathlib.Path(repo_path))
    if not config_data.get("exclude_signatures"):
        util.fail(
            util.style_warning("No signatures found in configuration, exiting..."),
            ctx,
            code=0,
        )

    scanner, stderr = scan_local_repo(
        options, repo_path, since_commit, max_depth, branch, include_submodules
    )

    if not scanner:
        # Explicitly fail if we didn't get a scanner back
        util.fail(util.style_error("Unable to update signatures"), ctx)

    plural = lambda n: "" if n == 1 else "s"
    deprecations = get_deprecations(stderr)
    ndeps = len(deprecations)
    click.echo(f"Found {ndeps} deprecated signature{plural(ndeps)}.")
    updated = replace_deprecated_signatures(deprecations, config_data)

    dups = 0
    if remove_duplicates:
        dups = remove_duplicated_entries(config_data)

    if update_configuration and (deprecations or dups):
        # Only rewrite the config if we have altered it
        write_updated_signatures(config_path, config_data)

        click.echo(f"Removed {dups} duplicated signature{plural(dups)}.")
        click.echo(f"Updated {updated} deprecated signature{plural(updated)}.")

    return scanner
