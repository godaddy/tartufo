# -*- coding: utf-8 -*-
import json
import os
import pathlib
import platform
import stat
import tempfile
import uuid
from datetime import datetime
from functools import lru_cache, partial
from hashlib import blake2s
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Pattern,
)

import click
import git
import pygit2

from tartufo import types
from tartufo.types import Rule

if TYPE_CHECKING:
    from tartufo.scanner import Issue  # pylint: disable=cyclic-import
    from tartufo.scanner import ScannerBase  # pylint: disable=cyclic-import
    from tartufo.config import OptionTypes  # pylint: disable=cyclic-import


DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def del_rw(_func: Callable, name: str, _exc: Exception) -> None:
    """Attempt to grant permission to and force deletion of a file.

    This is used as an error handler for `shutil.rmtree`.

    :param _func: The original calling function
    :param name: The name of the file to try removing
    :param _exc: The exception raised originally when the file was removed
    """
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def convert_regexes_to_rules(regexes: Dict[str, Pattern]) -> Dict[str, Rule]:
    return {
        name: Rule(name=name, pattern=pattern, path_pattern=None, re_match_type="match")
        for name, pattern in regexes.items()
    }


def echo_result(
    options: "types.GlobalOptions",
    scanner: "ScannerBase",
    repo_path: str,
    output_dir: Optional[pathlib.Path],
) -> None:
    """Print all found issues out to the console, optionally as JSON.
    :param options: Global options object
    :param scanner: ScannerBase containing issues and excluded paths from config tree
    :param repo_path: The path to the repository the issues were found in
    :param output_dir: The directory that issue details were written out to
    """

    now = datetime.now().isoformat("T", "microseconds")
    if options.output_format == types.OutputFormat.Json.value:
        output = {
            "scan_time": now,
            "project_path": repo_path,
            "output_dir": str(output_dir) if output_dir else None,
            "excluded_paths": [str(path.pattern) for path in scanner.excluded_paths],
            "excluded_signatures": [
                str(signature) for signature in options.exclude_signatures
            ],
            "exclude_entropy_patterns": [
                str(pattern) for pattern in options.exclude_entropy_patterns
            ],
            # This member is for reference. Read below...
            # "found_issues": [
            #     issue.as_dict(compact=options.compact) for issue in scanner.issues
            # ],
        }

        # Observation: We want to "stream" JSON; the only generator output is the
        # "found_issues" list (which is at the top level). Dump the "static" part
        # minus the closing "}", then generate issues individually, then emit the
        # closing "}".
        static_part = json.dumps(output)
        click.echo(f'{static_part[:-1]}, "found_issues": [', nl=False)
        delimiter = ""
        for issue in scanner.scan():
            compact = options.output_format == types.OutputFormat.Compact.value
            live_part = json.dumps(issue.as_dict(compact=compact))
            click.echo(f"{delimiter}{live_part}", nl=False)
            delimiter = ", "
        click.echo("]}")
    elif options.output_format == types.OutputFormat.Compact.value:
        for issue in scanner.scan():
            click.echo(
                f"[{issue.issue_type.value}] {issue.chunk.file_path}: {issue.matched_string} "
                f"({issue.signature}, {issue.issue_detail})"
            )
    else:
        for issue in scanner.scan():
            click.echo(bytes(issue))
        if not scanner.issues:
            if not options.quiet:
                click.echo(f"Time: {now}\nAll clear. No secrets detected.")
        if options.verbose > 0:
            click.echo("\nExcluded paths:")
            click.echo("\n".join([path.pattern for path in scanner.excluded_paths]))
            click.echo("\nExcluded signatures:")
            click.echo("\n".join(options.exclude_signatures))
            click.echo("\nExcluded entropy patterns:")
            click.echo("\n".join(options.exclude_entropy_patterns))


def write_outputs(found_issues: List["Issue"], output_dir: pathlib.Path) -> List[str]:
    """Write details of the issues to individual files in the specified directory.

    :param found_issues: A list of issues to be written out
    :param output_dir: The directory where the files should be written
    """
    result_files = []
    for issue in found_issues:
        result_file = output_dir / f"{uuid.uuid4()}.json"
        result_file.write_text(json.dumps(issue.as_dict()))
        result_files.append(str(result_file))
    return result_files


def clone_git_repo(
    git_url: str, target_dir: Optional[pathlib.Path] = None
) -> Tuple[pathlib.Path, str]:
    """Clone a remote git repository and return its filesystem path.

    :param git_url: The URL of the git repository to be cloned
    :param target_dir: Where to clone the repository to
    :returns: Filesystem path of local clone and name of remote source
    :raises types.GitRemoteException: If there was an error cloning the repository
    """
    if not target_dir:
        project_path = tempfile.mkdtemp()
    else:
        project_path = str(target_dir)

    try:
        repo = git.Repo.clone_from(git_url, project_path)
        origin = repo.remotes[0].name
    except git.GitCommandError as exc:
        raise types.GitRemoteException(exc.stderr.strip()) from exc
    return pathlib.Path(project_path), origin


style_ok = partial(click.style, fg="bright_green")  # pylint: disable=invalid-name
style_error = partial(click.style, fg="red", bold=True)  # pylint: disable=invalid-name
style_warning = partial(click.style, fg="bright_yellow")  # pylint: disable=invalid-name


def fail(msg: str, ctx: click.Context, code: int = 1) -> None:
    """Print out a styled error message and exit.

    :param msg: The message to print out to the user
    :param ctx: A context from a currently executing Click command
    :param code: The exit code to use; must be >= 1
    """
    click.echo(style_error(msg), err=True)
    ctx.exit(code)


@lru_cache(maxsize=None)
def generate_signature(snippet: str, filename: str) -> str:
    """Generate a stable hash signature for an issue found in a commit.

    These signatures are used for configuring excluded/approved issues,
    such as secrets intentionally embedded in tests.

    :param snippet: A string which was found as a potential issue during a scan
    :param filename: The file where the issue was found
    """
    return blake2s(f"{snippet}$${filename}".encode("utf-8")).hexdigest()


def extract_commit_metadata(
    commit: pygit2.Commit, branch: pygit2.Branch
) -> Dict[str, Any]:
    """Grab a consistent set of metadata from a git commit, for user output.

    :param commit: The commit to extract the data from
    :param branch: What branch the commit was found on
    """
    return {
        "commit_time": datetime.fromtimestamp(commit.commit_time).strftime(
            DATETIME_FORMAT
        ),
        "commit_message": commit.message,
        "commit_hash": commit.hex,
        "branch": branch.branch_name,
    }


def get_strings_of_set(
    word: str, char_set: Iterable[str], threshold: int = 20
) -> List[str]:
    """Split a "word" into a set of "strings", based on a given character set.

    The returned strings must have a length, at minimum, equal to `threshold`.
    This is meant for extracting long strings which are likely to be things like
    auto-generated passwords, tokens, hashes, etc.

    :param word: The word to be analyzed
    :param char_set: The set of characters used to compose the strings (i.e. hex)
    :param threshold: The minimum length for what is accepted as a string
    """
    count: int = 0
    letters: str = ""
    strings: List[str] = []

    for char in word:
        if char in char_set:
            letters += char
            count += 1
        else:
            if count > threshold:
                strings.append(letters)
            letters = ""
            count = 0
    if count > threshold:
        strings.append(letters)
    return strings


def path_contains_git(path: str) -> bool:
    try:
        return git.Repo(path) is not None
    except git.GitError:
        return False


def process_issues(
    repo_path: str,
    scan: "ScannerBase",
    options: types.GlobalOptions,
):
    now = datetime.now().isoformat("T", "microseconds")
    output_dir = None
    if options.output_dir:
        if platform.system().lower() == "windows":  # pragma: no cover
            # Make sure we aren't using illegal characters for Windows folder names
            now = now.replace(":", "")
        output_dir = pathlib.Path(options.output_dir) / f"tartufo-scan-results-{now}"
        output_dir.mkdir(parents=True)

    echo_result(options, scan, repo_path, output_dir)
    if output_dir:
        write_outputs(scan.issues, output_dir)
        if options.output_format != types.OutputFormat.Json.value:
            click.echo(f"Results have been saved in {output_dir}")
