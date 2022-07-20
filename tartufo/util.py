# -*- coding: utf-8 -*-
import json
import os
import pathlib
import platform
import stat
import sys
import tempfile
import uuid
from datetime import datetime
from functools import lru_cache, partial
from hashlib import blake2s
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    NoReturn,
    Tuple,
    TYPE_CHECKING,
    Pattern,
)

import click
import git
import pygit2

from tartufo import types

if TYPE_CHECKING:
    from tartufo.scanner import Issue  # pylint: disable=cyclic-import
    from tartufo.scanner import ScannerBase  # pylint: disable=cyclic-import


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
                str(signature) for signature in scanner.excluded_signatures
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
        if scanner.issue_count == 0:
            if not options.quiet:
                click.echo(f"Time: {now}\nAll clear. No secrets detected.")
        if options.verbose > 0:
            click.echo("\nExcluded paths:")
            click.echo("\n".join([str(path) for path in scanner.excluded_paths]))
            click.echo("\nExcluded signatures:")
            click.echo("\n".join(scanner.excluded_signatures))
            click.echo("\nExcluded entropy patterns:")
            click.echo("\n".join(str(path) for path in scanner.excluded_entropy))


def write_outputs(
    issues: Generator["Issue", None, None], output_dir: pathlib.Path
) -> List[str]:
    """Write details of the issues to individual files in the specified directory.

    :param found_issues: A list of issues to be written out
    :param output_dir: The directory where the files should be written
    """
    result_files = []
    for issue in issues:
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


if sys.stdout.isatty():
    style_ok = partial(click.style, fg="bright_green")
    style_error = partial(click.style, fg="red", bold=True)
    style_warning = partial(click.style, fg="bright_yellow")
else:
    # If stdout is not a TTY, don't include color - just pass the string back
    def _style_func(msg: str, *_: Any, **__: Any) -> str:
        # We define this func and pass it to partial still to preserve
        # typing integrity and prevent issues when callers expect to be
        # able to pass the same args as click.style accepts
        return msg

    style_ok = style_error = style_warning = partial(_style_func)


def fail(msg: str, ctx: click.Context, code: int = 1) -> NoReturn:
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


def extract_commit_metadata(commit: pygit2.Commit, branch_name: str) -> Dict[str, Any]:
    """Grab a consistent set of metadata from a git commit, for user output.

    :param commit: The commit to extract the data from
    :param branch_name: What branch the commit was found on
    """
    return {
        "commit_time": datetime.fromtimestamp(commit.commit_time).strftime(
            DATETIME_FORMAT
        ),
        "commit_message": commit.message,
        "commit_hash": commit.hex,
        "branch": branch_name,
    }


def find_strings_by_regex(
    text: str, regex: Pattern, threshold: int = 20
) -> Generator[str, None, None]:
    """Locate strings ("words") of interest in input text

    Each returned string must have a length, at minimum, equal to `threshold`.
    This is meant to return longer strings which are likely to be things like
    auto-generated passwords, tokens, hashes, etc.

    :param text: The text string to be analyzed
    :param regex: A pattern which matches all character sequences of interest
    :param threshold: The minimum acceptable length of a matching string
    """

    for match in regex.finditer(text):
        substring = match.group()
        if len(substring) >= threshold:
            yield substring


def path_contains_git(path: str) -> bool:
    """Determine whether a filesystem path contains a git repository.

    :param path: The fully qualified path to be checked
    """
    try:
        return git.Repo(path) is not None
    except git.GitError:
        return False


def process_issues(
    repo_path: str,
    scan: "ScannerBase",
    options: types.GlobalOptions,
) -> None:
    """Handle post-scan processing/reporting of a batch of issues.

    :param repo_path: The repository that was scanned
    :param scan: The scanner that performed the scan
    :param options: The options to use for determining output
    """
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
        write_outputs(scan.scan(), output_dir)
        if options.output_format != types.OutputFormat.Json.value:
            click.echo(f"Results have been saved in {output_dir}")


def is_shallow_clone(repo: pygit2.Repository) -> bool:
    """Determine whether a repository is a shallow clone

    This is used to work around https://github.com/libgit2/libgit2/issues/3058
    Basically, any time a git repository is a "shallow" clone (it was cloned
    with `--max-depth N`), git will create a file at `.git/shallow`. So we
    simply need to test whether that file exists to know whether we are
    interacting with a shallow repository.

    :param repo: The repository to check for "shallowness"
    """
    return (pathlib.Path(repo.path) / "shallow").exists()
