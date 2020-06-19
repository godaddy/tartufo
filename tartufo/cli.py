# -*- coding: utf-8 -*-

import pathlib
import shutil
from tempfile import mkdtemp
from typing import cast, List, Optional, Pattern, TextIO, Tuple

import click

from tartufo import config, scanner, util


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
    "--git-rules-repo",
    help="A file path, or git URL, pointing to a git repository containing regex "
    "rules to be used for scanning. By default, all .json files will be loaded "
    "from the root of that repository. --git-rules-files can be used to override "
    "this behavior and load specific files.",
)
@click.option(
    "--git-rules-files",
    multiple=True,
    help="Used in conjunction with --git-rules-repo, specify glob-style patterns "
    "for files from which to load the regex rules. Can be specified multiple times.",
)
@click.option(
    "--config",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        allow_dash=False,
    ),
    is_eager=True,
    callback=config.read_pyproject_toml,
    help="Read configuration from specified file. [default: pyproject.toml]",
)
@click.argument("git_url", required=False)
@click.pass_context
def main(ctx: click.Context, **kwargs: config.OptionTypes) -> None:
    """Find secrets hidden in the depths of git.

    Tartufo will, by default, scan the entire history of a git repository
    for any text which looks like a secret, password, credential, etc. It can
    also be made to work in pre-commit mode, for scanning blobs of text as a
    pre-commit hook.
    """
    if not any((kwargs["entropy"], kwargs["regex"])):
        util.fail("No analysis requested.", ctx)
    if not any((kwargs["pre_commit"], kwargs["repo_path"], kwargs["git_url"])):
        util.fail("You must specify one of --pre-commit, --repo-path, or git_url.", ctx)
    if kwargs["regex"]:
        try:
            rules_regexes = config.configure_regexes(
                cast(bool, kwargs["default_regexes"]),
                cast(Tuple[TextIO, ...], kwargs["rules"]),
                cast(Optional[str], kwargs["git_rules_repo"]),
                cast(Tuple[str, ...], kwargs["git_rules_files"]),
            )
        except ValueError as exc:
            util.fail(str(exc), ctx)
        if not rules_regexes:
            util.fail("Regex checks requested, but no regexes found.", ctx)
    else:
        rules_regexes = {}

    # read & compile path inclusion/exclusion patterns
    path_inclusions = []  # type: List[Pattern]
    path_exclusions = []  # type: List[Pattern]
    paths_file = cast(TextIO, kwargs["include_paths"])
    if paths_file:
        path_inclusions = config.compile_path_rules(paths_file.readlines())
    paths_file = cast(TextIO, kwargs["exclude_paths"])
    if paths_file:
        path_exclusions = config.compile_path_rules(paths_file.readlines())

    found_issues = []  # type: List[scanner.Issue]
    remove_repo = False
    if kwargs["pre_commit"]:
        repo_path = cast(str, kwargs["repo_path"])
        found_issues = scanner.find_staged(
            repo_path,
            cast(bool, kwargs["regex"]),
            cast(bool, kwargs["entropy"]),
            custom_regexes=rules_regexes,
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
        )
    else:
        if kwargs["git_url"]:
            repo_path = util.clone_git_repo(cast(str, kwargs["git_url"]))
            remove_repo = True
        else:
            repo_path = cast(str, kwargs["repo_path"])

        found_issues = scanner.scan_repo(
            repo_path, rules_regexes, path_inclusions, path_exclusions, kwargs
        )

    if found_issues:
        output_dir = pathlib.Path(mkdtemp())
        util.write_outputs(found_issues, output_dir)
    else:
        output_dir = None  # type: ignore
    util.echo_issues(found_issues, cast(bool, kwargs["json"]), repo_path, output_dir)

    if kwargs["cleanup"]:
        util.clean_outputs(output_dir)
    else:
        if output_dir and not kwargs["json"]:
            click.echo("Results have been saved in {}".format(output_dir))

    if remove_repo:
        shutil.rmtree(repo_path, onerror=util.del_rw)

    if found_issues:
        ctx.exit(1)
    ctx.exit(0)
