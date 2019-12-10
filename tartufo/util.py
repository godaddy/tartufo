# -*- coding: utf-8 -*-

import os
import shutil
import stat
import tempfile
from functools import partial
from typing import Callable

import click
from git import Repo


def del_rw(_func, name, _exc):
    # type: (Callable, str, Exception) -> None
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def clean_outputs(output):
    issues_path = output.get("issues_path", None)
    if issues_path and os.path.isdir(issues_path):
        shutil.rmtree(output["issues_path"])


def clone_git_repo(git_url):
    # type: (str) -> str
    project_path = tempfile.mkdtemp()
    Repo.clone_from(git_url, project_path)
    return project_path


style_ok = partial(click.style, fg="bright_green")  # pylint: disable=invalid-name
style_error = partial(  # pylint: disable=invalid-name
    click.style, fg="red", bold=True, err=True
)
style_warning = partial(click.style, fg="bright_yellow")  # pylint: disable=invalid-name
