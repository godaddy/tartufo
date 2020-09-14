# -*- coding: utf-8 -*-

import pathlib
from tempfile import mkdtemp
from typing import Any, Dict, List, Tuple

import click

from tartufo import config, scanner, types, util


PLUGIN_DIR = pathlib.Path(__file__).parent / "commands"


class TartufoCLI(click.MultiCommand):
    def list_commands(self, ctx: click.Context) -> List[str]:
        return [
            fpath.name[:-3].replace("_", "-")
            for fpath in PLUGIN_DIR.glob("*.py")
            if fpath.name != "__init__.py"
        ]

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command:
        exec_ns: Dict[str, Any] = {}
        cmd_file = PLUGIN_DIR / "{}.py".format(cmd_name.replace("-", "_"))
        with cmd_file.open() as handle:
            cmd_code = compile(handle.read(), cmd_file.name, "exec")
            eval(cmd_code, exec_ns, exec_ns)  # pylint: disable=eval-used
        return exec_ns["main"]


@click.command(
    cls=TartufoCLI,
    name="tartufo",
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
    "-e",
    "--exclude-signatures",
    multiple=True,
    help="Specify signatures of matches that you explicitly want to exclude "
    "from the scan, and mark as okay. These signatures are generated during "
    "the scan process, and reported out with each individual match. This "
    "option can be specified multiple times, to exclude as many signatures as "
    "you would like.",
)
@click.option(
    "--cleanup/--no-cleanup",
    is_flag=True,
    default=False,
    help="Clean up all temporary result files. [default: False]",
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
@click.pass_context
def main(ctx: click.Context, **kwargs: config.OptionTypes) -> None:
    """Find secrets hidden in the depths of git.

    Tartufo will, by default, scan the entire history of a git repository
    for any text which looks like a secret, password, credential, etc. It can
    also be made to work in pre-commit mode, for scanning blobs of text as a
    pre-commit hook.
    """
    options = types.GlobalOptions(**kwargs)  # type: ignore
    ctx.obj = options


@main.resultcallback()  # type: ignore
@click.pass_context
def process_issues(
    ctx: click.Context,
    result: Tuple[str, List[scanner.Issue]],
    **kwargs: config.OptionTypes,
):
    repo_path, issues = result
    options = types.GlobalOptions(**kwargs)  # type: ignore
    if issues:
        output_dir = pathlib.Path(mkdtemp())
        util.write_outputs(issues, output_dir)
    else:
        output_dir = None  # type: ignore
    util.echo_issues(issues, options.json, repo_path, output_dir)

    if options.cleanup:
        util.clean_outputs(output_dir)
    else:
        if output_dir and not options.json:
            click.echo("Results have been saved in {}".format(output_dir))

    if issues:
        ctx.exit(1)
    ctx.exit(0)
