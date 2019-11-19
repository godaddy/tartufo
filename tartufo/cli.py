# -*- coding: utf-8 -*-

import re
from functools import partial
from typing import cast, TextIO

import click
import truffleHogRegexes.regexChecks

from tartufo import config, scanner, util


err = partial(  # pylint: disable=invalid-name
    click.secho, fg="red", bold=True, err=True
)


@click.command(
    name="tartufo",  # noqa: C901
    context_settings=dict(help_option_names=["-h", "--help"]),
)
@click.option("--json/--no-json", help="Output in JSON format.", is_flag=True)
@click.option(
    "--rules",
    multiple=True,
    type=click.File("r"),
    help="Path(s) to regex rules json list file(s).",
)
@click.option(
    "--default-regexes/--no-default-regexes",
    is_flag=True,
    default=True,
    help="Whether to include the default regex list when configuring"
    " search patterns. Only applicable if --rules is also specified."
    " [default: --default-regexes]",
)
@click.option(
    "--entropy/--no-entropy",
    is_flag=True,
    default=True,
    help="Enable entropy checks. [default: True]",
)
@click.option(
    "--regex/--no-regex",
    is_flag=True,
    default=False,
    help="Enable high signal regexes checks. [default: False]",
)
@click.option("--since-commit", help="Only scan from a given commit hash.")
@click.option(
    "--max-depth",
    default=1000000,
    help="The max commit depth to go back when searching for secrets."
    " [default: 1000000]",
)
@click.option("--branch", help="Specify a branch name to scan only that branch.")
@click.option(
    "-i",
    "--include-paths",
    type=click.File("r"),
    help="File with regular expressions (one per line), at least one of "
    "which must match a Git object path in order for it to be scanned; "
    "lines starting with '#' are treated as comments and are ignored. "
    "If empty or not provided (default), all Git object paths are "
    "included unless otherwise excluded via the --exclude-paths option.",
)
@click.option(
    "-x",
    "--exclude-paths",
    type=click.File("r"),
    help="File with regular expressions (one per line), none of which may "
    "match a Git object path in order for it to be scanned; lines "
    "starting with '#' are treated as comments and are ignored. If "
    "empty or not provided (default), no Git object paths are excluded "
    "unless effectively excluded via the --include-paths option.",
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, allow_dash=False),
    help="Path to local repo clone. If provided, git_url will not be used.",
)
@click.option(
    "--cleanup/--no-cleanup",
    is_flag=True,
    default=False,
    help="Clean up all temporary result files. [default: False]",
)
@click.option(
    "--pre-commit",
    is_flag=True,
    default=False,
    help="Scan staged files in local repo clone.",
)
@click.option(
    "--config",
    type=click.File(mode="r"),
    is_eager=True,
    callback=config.read_pyproject_toml,
    help="Read configuration from specified file. [default: pyproject.toml]",
)
@click.argument("git_url", required=False)
@click.pass_context
def main(ctx, **kwargs):
    # type: (click.Context, config.OptionTypes) -> None
    """Find secrets hidden in the depths of git.

    Tartufo will, by default, scan the entire history of a git repository
    for any text which looks like a secret, password, credential, etc. It can
    also be made to work in pre-commit mode, for scanning blobs of text as a
    pre-commit hook.
    """
    if not any((kwargs["entropy"], kwargs["regex"])):
        err("No analysis requested.")
        ctx.exit(1)
    if not any((kwargs["pre_commit"], kwargs["repo_path"], kwargs["git_url"])):
        err("You must specify one of --pre-commit, --repo-path, or git_url.")
        ctx.exit(1)
    try:
        rules_regexes = config.configure_regexes_from_args(
            kwargs, truffleHogRegexes.regexChecks.regexes
        )
    except ValueError as exc:
        err(str(exc))
        ctx.exit(1)
    if kwargs["regex"] and not rules_regexes:
        err("Regex checks requested, but no regexes found.")
        ctx.exit(1)

    # read & compile path inclusion/exclusion patterns
    path_inclusions = []
    path_exclusions = []
    paths_file = cast(TextIO, kwargs["include_paths"])
    if paths_file:
        for pattern in [l[:-1].lstrip() for l in paths_file]:
            if pattern and not pattern.startswith("#"):
                path_inclusions.append(re.compile(pattern))
    paths_file = cast(TextIO, kwargs["exclude_paths"])
    if paths_file:
        for pattern in [l[:-1].lstrip() for l in paths_file]:
            if pattern and not pattern.startswith("#"):
                path_exclusions.append(re.compile(pattern))

    if kwargs["pre_commit"]:
        output = scanner.find_staged(
            cast(str, kwargs["repo_path"]),
            cast(bool, kwargs["json"]),
            cast(bool, kwargs["regex"]),
            cast(bool, kwargs["entropy"]),
            custom_regexes=rules_regexes,
            suppress_output=False,
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
        )
    else:
        output = scanner.find_strings(
            cast(str, kwargs["git_url"]),
            cast(str, kwargs["since_commit"]),
            cast(int, kwargs["max_depth"]),
            cast(bool, kwargs["json"]),
            cast(bool, kwargs["regex"]),
            cast(bool, kwargs["entropy"]),
            custom_regexes=rules_regexes,
            suppress_output=False,
            branch=cast(str, kwargs["branch"]),
            repo_path=cast(str, kwargs["repo_path"]),
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
        )

    if kwargs["cleanup"]:
        util.clean_outputs(output)
    else:
        issues_path = output.get("issues_path", None)
        if issues_path:
            print("Results have been saved in {}".format(issues_path))

    if output.get("found_issues", False):
        ctx.exit(1)
    ctx.exit(0)
