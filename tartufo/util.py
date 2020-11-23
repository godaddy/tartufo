# -*- coding: utf-8 -*-

import datetime
import json
import os
import pathlib
import stat
import tempfile
import uuid
import re
from functools import lru_cache, partial
from hashlib import blake2s
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    TYPE_CHECKING,
    Pattern,
    Tuple,
)

import click
import pygit2

from tartufo import types
from tartufo.types import Rule

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


def convert_regexes_to_rules(regexes: Dict[str, Pattern]) -> Dict[str, Rule]:
    return {
        name: Rule(name=name, pattern=pattern, path_pattern=None)
        for name, pattern in regexes.items()
    }


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


def _is_ssh(url: str) -> bool:
    if url.startswith("ssh://"):
        return True
    if re.search(r"(.+)\.(.+):(.*)", url) is not None:
        return True
    return False


def _is_https(url: str) -> bool:
    if url.startswith("https://"):
        return True
    return False


# pragma no cover
def get_repository(
    git_url: str,
    target_dir: Optional[str] = None,
    fetch: Optional[bool] = False,
    branch: Optional[str] = None,
) -> Tuple[pathlib.Path, pygit2.Repository]:

    repo: pygit2.Repository

    is_ssh = _is_ssh(git_url)
    if not is_ssh:
        is_https = _is_https(git_url)
    else:
        is_https = False

    if is_ssh or is_https:
        # This is a remote repo
        print("get_repository: " + git_url + " appears to be a remote repository")

        # Establish project_path
        if target_dir is None:
            print("get_repository: target_dir is None")
            project_path = tempfile.mkdtemp()
            print("get_repository: using mkdtemp(): " + project_path)
        else:
            print("get_repository: using target_dir: " + target_dir)
            project_path = target_dir

        git_path = pathlib.Path(project_path).expanduser().resolve()

        # We need to clone
        if not git_url.strip().startswith("https://"):
            # Assume git_url is ssh
            print(
                "get_repository: Clone ssh repo: " + git_url + " into " + project_path
            )
            repo = _clone_ssh_repo(git_url, project_path)
            print("get_repository: Skipping fetch because remote/ssh repo")
        else:
            # Assume git_url is https
            try:
                # TODO: Support https credentials as command line option
                print(
                    "get_repository: Clone https repo: "
                    + git_url
                    + " into "
                    + project_path
                )
                repo = pygit2.clone_repository(git_url, project_path)
                print("get_repository: Skipping fetch because remote/https repo")
            except pygit2.GitError as exc:
                raise types.GitRemoteException(str(exc)) from exc
    else:
        # This is a local repo
        git_path = pathlib.Path(git_url).absolute().expanduser()
        if not git_path.is_dir():
            print("get_repository: " + git_url + " does not exist as a directory")
            raise types.GitLocalException(
                git_url + " is not a valid git repository (does not exist)"
            )
        print("get_repository: " + git_url + " appears to exist as a directory")

        repo = pygit2.Repository(git_path)
        print("get_repository: pygit2.Repository(" + str(git_path) + ")")
        # We may need to fetch
        if fetch:
            if branch is not None:
                print("get_repository: Fetching single branch: " + branch)
                _fetch_ssh_repo(repo, branch)
            else:
                print("get_repository: Fetching all branches")
                _fetch_ssh_repo(repo)
        else:
            print("get_repository: Skipping fetch due to fetch == False")

    if repo.head is None:
        print("get_repository: Head is None")
    else:
        print("get_repository: Head is " + str(repo.head))
    print("get_repository: Repo is " + str(repo))

    return (git_path, repo)


# pragma no cover
def _fetch_ssh_repo(
    repo: pygit2.Repository, branch: Optional[str] = None
) -> pygit2.Repository:
    # TODO: Support Windows paths
    path_tuples = [
        ["~/.ssh/id_ed25519.pub", "~/.ssh/id_ed25519"],
        ["~/.ssh/id_rsa.pub", "~/.ssh/id_rsa"],
        ["~/.ssh/id_dsa.pub", "~/.ssh/id_dsa"],
    ]

    if branch is not None:
        print("fetch_ssh_repo(branch: " + branch + ")")
    else:
        print("fetch_ssh_repo()")

    for path_tuple in path_tuples:
        try:
            print("pub_key=" + path_tuple[0])
            pub_key = pathlib.Path(path_tuple[0]).expanduser()
            print("priv_key=" + path_tuple[1])
            priv_key = pathlib.Path(path_tuple[1]).expanduser()
            if not (pub_key.is_file() and priv_key.is_file()):
                print("Credentials don't exist")
                continue
            print("Have credentials")
            keypair = pygit2.Keypair("git", pub_key, priv_key, "")
            remote_callbacks = pygit2.RemoteCallbacks(credentials=keypair)
            if branch is not None:
                print("Fetching origin/" + branch)
                repo.remotes["origin"].fetch(branch, callbacks=remote_callbacks)
            else:
                print("Fetching all branches from origin")
                repo.remotes["origin"].fetch(callbacks=remote_callbacks)
            return repo

        except pygit2.GitError as exc:
            print(f"GitError raised: {exc}")
            # TODO: differentiate credentials errors from other errors
            continue
    raise types.GitRemoteException("Could not locate working ssh credentials")


# pragma no cover
def _clone_ssh_repo(git_url: str, project_path: str) -> pygit2.Repository:
    # TODO: Support Windows paths
    path_tuples = [
        ["~/.ssh/id_ed25519.pub", "~/.ssh/id_ed25519"],
        ["~/.ssh/id_rsa.pub", "~/.ssh/id_rsa"],
        ["~/.ssh/id_dsa.pub", "~/.ssh/id_dsa"],
    ]
    print("find_ssh_credentials")
    for path_tuple in path_tuples:
        try:
            print("pub_key=" + path_tuple[0])
            pub_key = pathlib.Path(path_tuple[0]).expanduser()
            print("priv_key=" + path_tuple[1])
            priv_key = pathlib.Path(path_tuple[1]).expanduser()
            if not (pub_key.is_file() and priv_key.is_file()):
                print("Credentials don't exist")
                continue
            print("Have credentials")
            keypair = pygit2.Keypair("git", pub_key, priv_key, "")
            remote_callbacks = pygit2.RemoteCallbacks(credentials=keypair)

            print("clone_repository(" + git_url + ")")
            repository = pygit2.clone_repository(
                git_url, project_path, callbacks=remote_callbacks
            )
            print("Successful clone")
            return repository

        except pygit2.GitError:
            print("GitError")
            # TODO: differentiate credentials errors from other errors
            continue
    raise types.GitRemoteException("Could not locate working ssh credentials")


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
    return blake2s("{}$${}".format(snippet, filename).encode("utf-8")).hexdigest()


def extract_commit_metadata(
    commit: pygit2.Commit, branch: pygit2.Branch
) -> Dict[str, Any]:
    """Grab a consistent set of metadata from a git commit, for user output.

    :param commit: The commit to extract the data from
    :param branch: What branch the commit was found on
    """
    return {
        "commit_time": datetime.datetime.fromtimestamp(commit.commit_time).strftime(
            DATETIME_FORMAT
        ),
        "commit_message": commit.message,
        "commit_hash": commit.hex,
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
