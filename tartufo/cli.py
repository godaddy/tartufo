# -*- coding: utf-8 -*-

import importlib
import logging
import pathlib
import warnings
from typing import List, Optional

import click

from tartufo import config, scanner, types


PLUGIN_DIR = pathlib.Path(__file__).parent / "commands"
PLUGIN_MODULE = "tartufo.commands"


class TartufoCLI(click.MultiCommand):
    _valid_commands: Optional[List[str]] = None

    @property
    def custom_commands(self):
        if self._valid_commands is None:
            self._valid_commands = [
                fpath.name[:-3].replace("_", "-")
                for fpath in PLUGIN_DIR.glob("*.py")
                if fpath.name != "__init__.py"
            ]
        return self._valid_commands

    def list_commands(self, ctx: click.Context) -> List[str]:
        return self.custom_commands

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        if cmd_name in self.custom_commands:
            module = importlib.import_module(
                f".{cmd_name.replace('-', '_')}", PLUGIN_MODULE
            )
            return module.main  # type: ignore
        return None


@click.command(
    cls=TartufoCLI,
    name="tartufo",
    context_settings=dict(help_option_names=["-h", "--help"]),
)
@click.option(
    "--rules",
    multiple=True,
    type=click.File("r"),
    help="[DEPRECATED] Use the rule-patterns config options instead. Path(s) to regex "
    "rules json list file(s).",
)
@click.option(
    "--rule-patterns",
    multiple=True,
    type=click.UNPROCESSED,
    hidden=True,
    help="Regular expression patterns to search the target for. May be specified multiple times.",
)
@click.option(
    "--default-regexes/--no-default-regexes",
    is_flag=True,
    default=True,
    show_default=True,
    help="Whether to include the default regex list when configuring"
    " search patterns. Only applicable if --rules is also specified.",
)
@click.option(
    "--entropy/--no-entropy",
    is_flag=True,
    default=True,
    show_default=True,
    help="Enable entropy checks.",
)
@click.option(
    "--regex/--no-regex",
    is_flag=True,
    default=True,
    show_default=True,
    help="Enable high signal regexes checks.",
)
@click.option(
    "--scan-filenames/--no-scan-filenames",
    is_flag=True,
    default=True,
    show_default=True,
    help="Check the names of files being scanned as well as their contents.",
)
@click.option(
    "-ip",
    "--include-path-patterns",
    multiple=True,
    hidden=True,
    type=click.UNPROCESSED,
    help="""Specify a regular expression which matches Git object paths to
    include in the scan. Multiple patterns can be included in the config file using
    include-path-patterns = [{path-pattern="pattern", reason="reason to include pattern},].
    If not provided (default), all Git object paths
    are included unless otherwise excluded via the --exclude-path-patterns
    option.""",
)
@click.option(
    "-xp",
    "--exclude-path-patterns",
    multiple=True,
    hidden=True,
    type=click.UNPROCESSED,
    help="""Specify a regular expression which matches Git object paths to
    exclude from the scan. Multiple patterns can be excluded in the config file using
    exclude-path-patterns = [{path-pattern="pattern", reason="reason to exclude pattern},].
    If not provided (default), no Git object paths
    are excluded unless effectively excluded via the --include-path-patterns
    option.""",
)
@click.option(
    "-of",
    "--output-format",
    type=click.Choice(
        [
            types.OutputFormat.Json.value,
            types.OutputFormat.Compact.value,
            types.OutputFormat.Text.value,
        ]
    ),
    default="text",
    help="""Specify the format in which the output needs to be generated
    `--output-format json/compact/text`. Either `json`, `compact` or `text`
    can be specified. If not provided (default) the output will be generated
    in `text` format.""",
)
@click.option(
    "-xe",
    "--exclude-entropy-patterns",
    multiple=True,
    hidden=True,
    type=click.UNPROCESSED,
    help="""Specify a regular expression which matches entropy strings to exclude from the scan. This option can be
    specified multiple times to exclude multiple patterns. If not provided (default), no entropy strings will be
    excluded. ({"path-pattern": {path regex}, "pattern": {pattern regex}, "match-type": "match"|"search",
    "scope": "word"|"line"}).""",
)
@click.option(
    "-e",
    "--exclude-signatures",
    multiple=True,
    hidden=True,
    type=click.UNPROCESSED,
    help="Specify signatures of matches that you explicitly want to exclude "
    "from the scan along with the reason, and mark as okay. These signatures "
    "are generated during the scan process, and reported out with each"
    "individual match. This option can be specified multiple times, "
    "to exclude as many signatures as you would like. "
    "{signature='signature', reason='The reason of excluding the signature'}",
)
@click.option(
    "-od",
    "--output-dir",
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        allow_dash=False,
    ),
    help="If specified, all issues will be written out as individual JSON files "
    "to a uniquely named directory under this one. This will help with keeping "
    "the results of individual runs of tartufo separated.",
)
@click.option(
    "-td",
    "--temp-dir",
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        allow_dash=False,
    ),
    help="If specified, temporary files will be written to the specified path",
)
@click.option(
    "--buffer-size",
    type=int,
    default=10000,
    show_default=True,
    help="Maximum number of issue to buffer in memory before shifting to temporary file buffering",
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
    help="Read configuration from specified file. [default: tartufo.toml]",
)
@click.option(
    "-q/ ",
    "--quiet/--no-quiet",
    help="Quiet mode. No outputs are reported if the scan is successful and doesn't "
    "find any issues",
    default=False,
    is_flag=True,
)
@click.option(
    "-v/ ",
    "--verbose",
    help="Display more verbose output. Specifying this option multiple times will "
    "incrementally increase the amount of output.",
    default=0,
    count=True,
)
@click.option(
    "--log-timestamps/--no-log-timestamps",
    is_flag=True,
    default=True,
    show_default=True,
    help="Enable or disable timestamps in logging messages.",
)
@click.option(
    "--entropy-sensitivity",
    type=click.IntRange(0, 100),
    default=75,
    show_default=True,
    help="""Modify entropy detection sensitivity. This is expressed as on a scale
    of 0 to 100, where 0 means "totally nonrandom" and 100 means "totally random".
    Decreasing the scanner's sensitivity increases the likelihood that a given
    string will be identified as suspicious.""",
)
@click.option(
    "-b64",
    "--b64-entropy-score",
    help="""[DEPRECATED] Use `--entropy-sensitivity`. Modify the base64 entropy score. If
    a value greater than the default (4.5 in a range of 0.0-6.0) is specified,
    tartufo lists higher entropy base64 strings (longer or more randomized strings.
    A lower value lists lower entropy base64 strings (shorter or less randomized
    strings).""",
)
@click.option(
    "-hex",
    "--hex-entropy-score",
    help="""[DEPRECATED] Use `--entropy-sensitivity`. Modify the hexadecimal entropy score.
    If a value greater than the default (3.0 in a range of 0.0-4.0) is specified,
    tartufo lists higher entropy hexadecimal strings (longer or more randomized
    strings). A lower value lists lower entropy hexadecimal strings (shorter or less
    randomized strings).""",
)
# The first positional argument here would be a hard-coded version, hence the `None`
@click.version_option(None, "-V", "--version")
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
    if options.quiet and options.verbose > 0:
        raise click.BadParameter("-v/--verbose and -q/--quiet are mutually exclusive.")

    logger = logging.getLogger()
    git_logger = logging.getLogger("git")
    # Make sure we don't exceed the maximum log level
    if options.verbose > 3:
        excess_verbosity = options.verbose - 3
        options.verbose = 3
        excess_verbosity = min(excess_verbosity, 3)
    else:
        excess_verbosity = 0

    # Log warnings by default, unless quiet
    default_level = 1 if not options.quiet else 0
    # Translate the number of "verbose" arguments, to an actual logging level
    level_name = types.LogLevel(max(options.verbose, default_level)).name
    logger.setLevel(getattr(logging, level_name))
    # Pass any excess verbosity down to the git logger, for extreme debugging needs
    git_logger.setLevel(getattr(logging, types.LogLevel(excess_verbosity).name))

    handler = logging.StreamHandler()
    if not excess_verbosity:
        # Example: [2021-02-11 10:28:08,445] [INFO] - Starting scan...
        log_format = "[%(levelname)s] - %(message)s"
    else:
        # Also show the logger name to help differentiate messages
        log_format = "[%(levelname)s] [%(name)s] - %(message)s"
    if options.log_timestamps:
        log_format = " ".join(["[%(asctime)s]", log_format])
    handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(handler)
    # Show deprecation warnings to the console by default
    warnings.simplefilter("always", DeprecationWarning)


@main.result_callback()  # type: ignore
@click.pass_context
def process_exit(
    ctx: click.Context,
    scan: scanner.ScannerBase,
    **_kwargs: config.OptionTypes,
):
    if scan.issue_count > 0:
        ctx.exit(1)

    ctx.exit(0)
