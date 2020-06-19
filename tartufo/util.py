# -*- coding: utf-8 -*-

import json
import os
import pathlib
import shutil
import stat
import tempfile
import uuid
from functools import partial
from typing import Callable, List, TYPE_CHECKING

import click
from git import Repo

if TYPE_CHECKING:
    from tartufo.scanner import Issue  # pylint: disable=cyclic-import


def del_rw(_func: Callable, name: str, _exc: Exception) -> None:
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def echo_issues(
    issues: "List[Issue]", as_json: bool, repo_path: str, output_dir: pathlib.Path
) -> None:
    """Print all found issues out to the console, optionally as JSON."""
    if as_json:
        output = {
            "project_path": repo_path,
            "issues_path": output_dir,
            "found_issues": [issue.as_dict() for issue in issues],
        }
        click.echo(json.dumps(output))
    else:
        for issue in issues:
            click.echo(issue)


def write_outputs(found_issues: "List[Issue]", output_dir: pathlib.Path) -> List[str]:
    result_files = []
    for issue in found_issues:
        result_file = output_dir / str(uuid.uuid4())
        result_file.write_text(json.dumps(issue.as_dict()))
        result_files.append(str(result_file))
    return result_files


def clean_outputs(output_dir: pathlib.Path) -> None:
    if output_dir and output_dir.is_dir():
        shutil.rmtree(output_dir)


def clone_git_repo(git_url: str) -> str:
    project_path = tempfile.mkdtemp()
    Repo.clone_from(git_url, project_path)
    return project_path


style_ok = partial(click.style, fg="bright_green")  # pylint: disable=invalid-name
style_error = partial(click.style, fg="red", bold=True)  # pylint: disable=invalid-name
style_warning = partial(click.style, fg="bright_yellow")  # pylint: disable=invalid-name


def fail(msg: str, ctx: click.Context, code: int = 1) -> None:
    """Print out a styled error message and exit."""
    click.echo(style_error(msg), err=True)
    ctx.exit(code)
