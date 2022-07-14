import contextlib
import functools
import io
import pathlib
import re
import typing as t

import click
import tomlkit

from tartufo import types, util
from tartufo.config import load_config_from_path
from tartufo.scanner import GitRepoScanner


def _scan_local_repo(
    options: types.GlobalOptions,
    repo_path: str,
    since_commit: t.Optional[str],
    max_depth: int,
    branch: t.Optional[str],
    include_submodules: bool,
) -> t.Union[GitRepoScanner, None]:
    """We had to duplicate the scan local repo command callback, to
    alter the exception logic a bit and prevent swallowing errors.
    """
    git_options = types.GitOptions(
        since_commit=since_commit,
        max_depth=max_depth,
        branch=branch,
        include_submodules=include_submodules,
    )

    try:
        scanner = GitRepoScanner(options, git_options, str(repo_path))
        util.process_issues(repo_path, scanner, options)
    except types.GitLocalException:
        message = f"{repo_path} is not a valid git repository."
        click.echo(util.style_error(message), err=True)
        return None
    except types.TartufoException as exc:
        click.echo(util.style_error(str(exc)), err=True)
        return None

    return scanner


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
@click.pass_obj
@click.pass_context
def main(
    ctx: click.Context,
    options: types.GlobalOptions,
    repo_path: str,
    since_commit: t.Optional[str],
    max_depth: int,
    branch: t.Optional[str],
    include_submodules: bool,
) -> GitRepoScanner:
    """Scan a local repository and update any deprecated signatures."""
    config_path, config_data = load_config_from_path(pathlib.Path(repo_path))
    if not config_data.get("exclude_signatures"):
        util.fail(
            util.style_warning("No signatures found in configuration, exiting..."), ctx
        )

    stdout = io.StringIO()
    stderr = io.StringIO()
    deprecations = set()
    deprecation_rgx = re.compile(
        r"DeprecationWarning: Signature (\w+) was.*use signature (\w+) instead\."
    )

    with contextlib.redirect_stdout(stdout):
        with contextlib.redirect_stderr(stderr):
            # Deprecation warnings are printed to stderr
            scanner = _scan_local_repo(
                options, repo_path, since_commit, max_depth, branch, include_submodules
            )

    del stdout  # We are discarding stdout from the scan-local-repo command
    # Should we print it to the user instead?

    if not scanner:
        # Explicitly fail if we didn't get a scanner back
        util.fail(util.style_error("Unable to update signatures"), ctx)

    # Start at the beginning of the buffer
    stderr.seek(0)
    for line in stderr:
        match = deprecation_rgx.search(line)

        if match:
            # This line had a deprecation warning
            deprecations.add(match.groups())

    click.echo(f"Found {len(deprecations)} unique deprecated signatures.")
    for (i, (old_sig, new_sig)) in enumerate(deprecations):
        targets = functools.partial(lambda o, s: o == s["signature"], old_sig)
        # Iterate all the deprecations and update them everywhere
        # they are found in the exclude-signatures section of config
        for target_signature in filter(targets, config_data["exclude_signatures"]):
            click.echo(f"{i + 1}) Updating {old_sig!r} -> {new_sig!r}")
            target_signature["signature"] = new_sig

    # Read the current config, for clean overwrite
    with open(str(config_path), "r") as file:
        result = tomlkit.loads(file.read())

    # Assign the new signatures and write it to the config
    result["tool"]["tartufo"]["exclude-signatures"] = config_data[  # type: ignore
        "exclude_signatures"
    ]

    with open(str(config_path), "w") as file:
        file.write(tomlkit.dumps(result))

    # We would have failed earlier so this assert is safe
    assert scanner is not None
    return scanner
