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

if TYPE_CHECKING:
    from tartufo.scanner import Issue  # pylint: disable=cyclic-import


DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def del_rw(_func: Callable, name: str, _exc: Exception) -> None:
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def echo_issues(
    issues: "List[Issue]",
    as_json: bool,
    repo_path: str,
    output_dir: Optional[pathlib.Path],
) -> None:
    """Print all found issues out to the console, optionally as JSON."""
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
    result_files = []
    for issue in found_issues:
        result_file = output_dir / f"{uuid.uuid4()}.json"
        result_file.write_text(json.dumps(issue.as_dict()))
        result_files.append(str(result_file))
    return result_files


def clone_git_repo(
    git_url: str, target_dir: Optional[pathlib.Path] = None
) -> pathlib.Path:
    if not target_dir:
        project_path = tempfile.mkdtemp()
    else:
        project_path = str(target_dir)

    git.Repo.clone_from(git_url, project_path)
    return pathlib.Path(project_path)


style_ok = partial(click.style, fg="bright_green")  # pylint: disable=invalid-name
style_error = partial(click.style, fg="red", bold=True)  # pylint: disable=invalid-name
style_warning = partial(click.style, fg="bright_yellow")  # pylint: disable=invalid-name


def fail(msg: str, ctx: click.Context, code: int = 1) -> None:
    """Print out a styled error message and exit."""
    click.echo(style_error(msg), err=True)
    ctx.exit(code)


@lru_cache()
def generate_signature(snippet: str, filename: str) -> str:
    """Generate a stable hash signature for an issue found in a commit.

    These signatures are used for configuring excluded/approved issues,
    such as secrets intentionally embedded in tests."""
    return blake2s("{}$${}".format(snippet, filename).encode("utf-8")).hexdigest()


def extract_commit_metadata(
    commit: git.Commit, branch: git.FetchInfo
) -> Dict[str, Any]:
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
