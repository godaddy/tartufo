# -*- coding: utf-8 -*-

import datetime
import json
import os
import pathlib
import stat
import tempfile
import uuid
from functools import lru_cache, partial
from hashlib import blake2s
from typing import Any, Callable, Dict, Iterable, List, Optional, TYPE_CHECKING

import click
import git

from tartufo import types

if TYPE_CHECKING:
    from tartufo.scanner import Issue  # pylint: disable=cyclic-import


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


def echo_issues(
    issues: "List[Issue]",
    as_json: bool,
    repo_path: str,
    output_dir: Optional[pathlib.Path],
) -> None:
    """Print all found issues out to the console, optionally as JSON.

    :param issues: The list of issues to be printed out
    :param as_json: Whether the output should be formatted as JSON
    :param repo_path: The path to the repository the issues were found in
    :param output_dir: The directory that issue details were written out to
    """
    if as_json:
        output = {
            "project_path": repo_path,
            "output_dir": str(output_dir) if output_dir else None,
            "found_issues": [issue.as_dict() for issue in issues],
        }
        click.echo(json.dumps(output))
    else:
        for issue in issues:
            click.echo(issue)


def write_outputs(found_issues: "List[Issue]", output_dir: pathlib.Path) -> List[str]:
    """Write details of the issues to individual files in the specified directory.

    :param found_issues: The list of issues to be written out
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
) -> pathlib.Path:
    """Clone a remote git repository and return its filesystem path.

    :param git_url: The URL of the git repository to be cloned
    :param target_dir: Where to clone the repository to
    :raises types.GitRemoteException: If there was an error cloning the repository
    """
    if not target_dir:
        project_path = tempfile.mkdtemp()
    else:
        project_path = str(target_dir)

    try:
        git.Repo.clone_from(git_url, project_path)
    except git.GitCommandError as exc:
        raise types.GitRemoteException(exc.stderr.strip()) from exc
    return pathlib.Path(project_path)


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


@lru_cache()
def generate_signature(snippet: str, filename: str) -> str:
    """Generate a stable hash signature for an issue found in a commit.

    These signatures are used for configuring excluded/approved issues,
    such as secrets intentionally embedded in tests.

    :param snippet: A string which was found as a potential issue during a scan
    :param filename: The file where the issue was found
    """
    return blake2s("{}$${}".format(snippet, filename).encode("utf-8")).hexdigest()


def extract_commit_metadata(
    commit: git.Commit, branch: git.FetchInfo
) -> Dict[str, Any]:
    """Grab a consistent set of metadata from a git commit, for user output.

    :param commit: The commit to extract the data from
    :param branch: What branch the commit was found on
    """
    return {
        "commit_time": datetime.datetime.fromtimestamp(commit.committed_date).strftime(
            DATETIME_FORMAT
        ),
        "commit_message": commit.message,
        "commit_hash": commit.hexsha,
        "branch": branch.name,
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
