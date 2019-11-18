# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import uuid
from typing import Dict, Iterable, List, Optional, Pattern, Set, Union

import git

from tartufo import util


BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
HEX_CHARS = "1234567890abcdefABCDEF"

# FIXME: This should be replaced with a dataclass to better track the attributes
IssueDict = Dict[str, Union[str, List[str]]]
PatternDict = Dict[str, Union[str, Pattern]]


class Bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    def __init__(self, name):
        # type: (str) -> None
        self.name = name


def shannon_entropy(data, iterator):
    # type: (str, Iterable[str]) -> float
    """
    Borrowed from http://blog.dkbza.org/2007/05/scanning-data-for-entropy-anomalies.html
    """
    if not data:
        return 0.0
    entropy = 0.0
    for inter_x in iterator:
        p_x = float(data.count(inter_x)) / len(data)
        if p_x > 0:
            entropy += -p_x * math.log(p_x, 2)
    return entropy


def get_strings_of_set(word, char_set, threshold=20):
    # type: (str, Iterable[str], int) -> List[str]
    count = 0
    letters = ""
    strings = []
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


def print_results(print_json, issue):
    # type: (bool, IssueDict) -> None
    if print_json:
        print(json.dumps(issue, sort_keys=True))
    else:
        printable_diff = issue["printDiff"]
        for string in issue["strings_found"]:
            printable_diff = printable_diff.replace(  # type: ignore
                string, Bcolors.WARNING + string + Bcolors.ENDC
            )
        print("~~~~~~~~~~~~~~~~~~~~~")
        if "reason" in issue:
            print(
                "{}Reason: {}{}".format(Bcolors.OKGREEN, issue["reason"], Bcolors.ENDC)
            )
        if "date" in issue:
            print("{}Date: {}{}".format(Bcolors.OKGREEN, issue["date"], Bcolors.ENDC))
        if "commit_hash" in issue:
            print(
                "{}Hash: {}{}".format(
                    Bcolors.OKGREEN, issue["commit_hash"], Bcolors.ENDC
                )
            )
        if "path" in issue:
            print(
                "{}Filepath: {}{}".format(Bcolors.OKGREEN, issue["path"], Bcolors.ENDC)
            )

        if sys.version_info >= (3, 0):
            if "branch" in issue:
                print(
                    "{}Branch: {}{}".format(
                        Bcolors.OKGREEN, issue["branch"], Bcolors.ENDC
                    )
                )
            if "commit" in issue:
                print(
                    "{}Commit: {}{}".format(
                        Bcolors.OKGREEN, issue["commit"], Bcolors.ENDC
                    )
                )
            print(printable_diff)
        else:
            if "branch" in issue:
                print(
                    "{}Branch: {}{}".format(
                        Bcolors.OKGREEN, issue["branch"].encode("utf-8"), Bcolors.ENDC
                    )
                )
            if "commit" in issue:
                print(
                    "{}Commit: {}{}".format(
                        Bcolors.OKGREEN, issue["commit"].encode("utf-8"), Bcolors.ENDC
                    )
                )
            print(printable_diff.encode("utf-8"))
        print("~~~~~~~~~~~~~~~~~~~~~")


def find_entropy(printable_diff):
    # type: (str) -> List[Dict[str, Union[str, List[str]]]]
    strings_found = []
    lines = printable_diff.split("\n")
    for line in lines:
        for word in line.split():
            base64_strings = get_strings_of_set(word, BASE64_CHARS)
            hex_strings = get_strings_of_set(word, HEX_CHARS)
            for string in base64_strings:
                b64_entropy = shannon_entropy(string, BASE64_CHARS)
                if b64_entropy > 4.5:
                    strings_found.append(string)
            for string in hex_strings:
                hex_entropy = shannon_entropy(string, HEX_CHARS)
                if hex_entropy > 3:
                    strings_found.append(string)
    if strings_found:
        entropic_diff = {}  # type: Dict[str, Union[str, List[str]]]
        entropic_diff["strings_found"] = strings_found
        entropic_diff["reason"] = "High Entropy"
        return [entropic_diff]
    return []


def find_regex(printable_diff, regex_list=None):
    # type: (str, Optional[PatternDict]) -> List[IssueDict]
    if regex_list is None:
        regex_list = {}
    regex_matches = []
    for key in regex_list:
        found_strings = regex_list[key].findall(printable_diff)  # type: ignore
        if found_strings:
            found_regex = {}
            found_regex["strings_found"] = found_strings
            found_regex["reason"] = key
            regex_matches.append(found_regex)
    return regex_matches


def diff_worker(
    diff,  # type: git.Diff
    custom_regexes,  # type: Optional[PatternDict]
    do_entropy,  # type: bool
    do_regex,  # type: bool
    print_json,  # type: bool
    suppress_output,  # type: bool
    path_inclusions,  # type: Optional[Iterable[Pattern]]
    path_exclusions,  # type: Optional[Iterable[Pattern]]
    prev_commit=None,  # type: Optional[git.Commit]
    branch_name=None,  # type: Optional[str]
):
    # type: (...) -> List[IssueDict]
    issues = []  # type: List[IssueDict]
    for blob in diff:
        printable_diff = blob.diff.decode("utf-8", errors="replace")
        if printable_diff.startswith("Binary files"):
            continue
        if not path_included(blob, path_inclusions, path_exclusions):
            continue
        if prev_commit is not None:
            commit_time = datetime.datetime.fromtimestamp(
                prev_commit.committed_date
            ).strftime("%Y-%m-%d %H:%M:%S")
        else:
            commit_time = ""
        found_issues = []  # type: List[IssueDict]
        if do_entropy:
            found_issues = find_entropy(printable_diff)
        if do_regex:
            found_issues += find_regex(printable_diff, custom_regexes)
        for finding in found_issues:
            # FIXME: This is relying on side effects to modify the origin dict
            finding["path"] = blob.b_path if blob.b_path else blob.a_path
            finding["diff"] = blob.diff.decode("utf-8", errors="replace")
            finding["printDiff"] = printable_diff
            if prev_commit is not None:
                finding["date"] = commit_time
                finding["commit"] = prev_commit.message
                finding["commit_hash"] = prev_commit.hexsha
            if branch_name is not None:
                finding["branch"] = branch_name
            if not suppress_output:
                print_results(print_json, finding)
        issues += found_issues
    return issues


def handle_results(output, output_dir, found_issues):
    # type: (IssueDict, str, Iterable[IssueDict]) -> IssueDict
    for found_issue in found_issues:
        result_path = os.path.join(output_dir, str(uuid.uuid4()))
        with open(result_path, "w+") as result_file:
            result_file.write(json.dumps(found_issue))
        output["found_issues"].append(result_path)  # type: ignore
    return output


def path_included(blob, include_patterns=None, exclude_patterns=None):
    # type: (git.Blob, Optional[Iterable[Pattern]], Optional[Iterable[Pattern]]) -> bool
    """Check if the diff blob object should included in analysis.

    If defined and non-empty, `include_patterns` has precedence over `exclude_patterns`, such that a blob that is not
    matched by any of the defined `include_patterns` will be excluded, even when it is not matched by any of the defined
    `exclude_patterns`. If either `include_patterns` or `exclude_patterns` are undefined or empty, they will have no
    effect, respectively. All blobs are included by this function when called with default arguments.

    :param blob: a Git diff blob object
    :param include_patterns: iterable of compiled regular expression objects; when non-empty, at least one pattern must
     match the blob object for it to be included; if empty or None, all blobs are included, unless excluded via
     `exclude_patterns`
    :param exclude_patterns: iterable of compiled regular expression objects; when non-empty, _none_ of the patterns may
     match the blob object for it to be included; if empty or None, no blobs are excluded if not otherwise
     excluded via `include_patterns`
    :return: False if the blob is _not_ matched by `include_patterns` (when provided) or if it is matched by
    `exclude_patterns` (when provided), otherwise returns True
    """
    path = blob.b_path if blob.b_path else blob.a_path
    if include_patterns and not any(p.match(path) for p in include_patterns):
        return False
    if exclude_patterns and any(p.match(path) for p in exclude_patterns):
        return False
    return True


def find_strings(
    git_url,  # type: str
    since_commit=None,  # type: Optional[str]
    max_depth=1000000,  # type: int
    print_json=False,  # type: bool
    do_regex=False,  # type: bool
    do_entropy=True,  # type: bool
    suppress_output=True,  # type: bool
    custom_regexes=None,  # type: Optional[PatternDict]
    branch=None,  # type: Optional[str]
    repo_path=None,  # type: Optional[str]
    path_inclusions=None,  # type: Optional[Iterable[Pattern]]
    path_exclusions=None,  # type: Optional[Iterable[Pattern]]
):
    # type: (...) -> IssueDict
    output = {"found_issues": []}  # type: IssueDict
    if repo_path:
        project_path = repo_path
    else:
        project_path = util.clone_git_repo(git_url)
    repo = git.Repo(project_path)
    already_searched = set()  # type: Set[bytes]
    output_dir = tempfile.mkdtemp()

    if branch:
        branches = repo.remotes.origin.fetch(branch)
    else:
        branches = repo.remotes.origin.fetch()

    for remote_branch in branches:
        since_commit_reached = False
        branch_name = remote_branch.name
        prev_commit = None
        curr_commit = None
        commit_hash = None
        for curr_commit in repo.iter_commits(branch_name, max_count=max_depth):
            commit_hash = curr_commit.hexsha
            if commit_hash == since_commit:
                since_commit_reached = True
            if since_commit and since_commit_reached:
                prev_commit = curr_commit
                continue
            # if not prev_commit, then curr_commit is the newest commit. And we have nothing to diff with.
            # But we will diff the first commit with NULL_TREE here to check the oldest code.
            # In this way, no commit will be missed.
            diff_hash = hashlib.md5(
                (str(prev_commit) + str(curr_commit)).encode("utf-8")
            ).digest()
            if not prev_commit or diff_hash in already_searched:
                prev_commit = curr_commit
                continue
            diff = prev_commit.diff(curr_commit, create_patch=True)
            # avoid searching the same diffs
            already_searched.add(diff_hash)
            found_issues = diff_worker(
                diff,
                custom_regexes,
                do_entropy,
                do_regex,
                print_json,
                suppress_output,
                path_inclusions,
                path_exclusions,
                prev_commit,
                branch_name,
            )
            output = handle_results(output, output_dir, found_issues)
            prev_commit = curr_commit
        # Handling the first commit
        diff = curr_commit.diff(git.NULL_TREE, create_patch=True)
        found_issues = diff_worker(
            diff,
            custom_regexes,
            do_entropy,
            do_regex,
            print_json,
            suppress_output,
            path_inclusions,
            path_exclusions,
            prev_commit,
            branch_name,
        )
        output = handle_results(output, output_dir, found_issues)
    output["project_path"] = project_path
    output["clone_uri"] = git_url
    output["issues_path"] = output_dir
    if not repo_path:
        shutil.rmtree(project_path, onerror=util.del_rw)
    return output


def find_staged(
    project_path,  # type: str
    print_json=False,  # type: bool
    do_regex=False,  # type: bool
    do_entropy=True,  # type: bool
    suppress_output=True,  # type: bool
    custom_regexes=None,  # type: Optional[PatternDict]
    path_inclusions=None,  # type: Optional[Iterable[Pattern]]
    path_exclusions=None,  # type: Optional[Iterable[Pattern]]
):
    # type: (...) -> IssueDict
    output = {"found_issues": []}  # type: IssueDict
    output_dir = tempfile.mkdtemp()
    repo = git.Repo(project_path, search_parent_directories=True)
    # using "create_patch=True" below causes output list to be empty
    # unless "R=True" also is specified. See GitPython issue 852:
    # https://github.com/gitpython-developers/GitPython/issues/852
    diff = repo.index.diff(repo.head.commit, create_patch=True, R=True)
    found_issues = diff_worker(
        diff,
        custom_regexes,
        do_entropy,
        do_regex,
        print_json,
        suppress_output,
        path_inclusions,
        path_exclusions,
    )

    output = handle_results(output, output_dir, found_issues)
    output["project_path"] = project_path
    output["issues_path"] = output_dir
    return output
