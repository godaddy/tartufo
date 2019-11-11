# -*- coding: utf-8 -*-

import argparse
import os
import shutil
import stat
import tempfile
from typing import Callable

from git import Repo


def del_rw(_func, name, _exc):
    # type: (Callable, str, Exception) -> None
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def clean_outputs(output):
    issues_path = output.get("issues_path", None)
    if issues_path and os.path.isdir(issues_path):
        shutil.rmtree(output["issues_path"])


def str2bool(v_string):
    # type: (str) -> bool
    if v_string is None:
        return True

    if v_string.lower() in ("yes", "true", "t", "y", "1"):
        return True

    if v_string.lower() in ("no", "false", "f", "n", "0"):
        return False

    raise argparse.ArgumentTypeError("Boolean value expected.")


def clone_git_repo(git_url):
    # type: (str) -> str
    project_path = tempfile.mkdtemp()
    Repo.clone_from(git_url, project_path)
    return project_path
