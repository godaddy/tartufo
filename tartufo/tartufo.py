#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Stops warning about module name
# pylint: disable=C0103
# pylint: enable=C0103
# pylint: disable=C0330

from __future__ import print_function
from __future__ import absolute_import

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import shutil
import stat
import sys
import tempfile
import uuid

from git import NULL_TREE
from git import Repo
from truffleHogRegexes.regexChecks import regexes


def main():  # noqa:C901
    parser = argparse.ArgumentParser(
        description="Find secrets hidden in the depths of git."
    )
    parser.add_argument(
        "--json", dest="output_json", action="store_true", help="Output in JSON"
    )
    parser.add_argument(
        "--rules",
        dest="rules",
        default={},
        help="Ignore default regexes and source from json list file",
    )
    parser.add_argument(
        "--entropy",
        dest="do_entropy",
        metavar="BOOLEAN",
        nargs="?",
        default="True",
        const="True",
        help="Enable entropy checks [default: True]",
    )
    parser.add_argument(
        "--regex",
        dest="do_regex",
        metavar="BOOLEAN",
        nargs="?",
        default="False",
        const="True",
        help="Enable high signal regex checks [default: False]",
    )
    parser.add_argument(
        "--since_commit",
        dest="since_commit",
        default=None,
        help="Only scan from a given commit hash",
    )
    parser.add_argument(
        "--max_depth",
        dest="max_depth",
        default=1000000,
        help="The max commit depth to go back when searching for " "secrets",
    )
    parser.add_argument(
        "--branch", dest="branch", default=None, help="Name of the branch to be scanned"
    )
    parser.add_argument(
        "-i",
        "--include_paths",
        type=argparse.FileType("r"),
        metavar="INCLUDE_PATHS_FILE",
        help="File with regular expressions (one per line), at least one of which must match a Git "
        'object path in order for it to be scanned; lines starting with "#" are treated as '
        "comments and are ignored. If empty or not provided (default), all Git object paths are "
        "included unless otherwise excluded via the --exclude_paths option.",
    )
    parser.add_argument(
        "-x",
        "--exclude_paths",
        type=argparse.FileType("r"),
        metavar="EXCLUDE_PATHS_FILE",
        help="File with regular expressions (one per line), none of which may match a Git object path "
        'in order for it to be scanned; lines starting with "#" are treated as comments and are '
        "ignored. If empty or not provided (default), no Git object paths are excluded unless "
        "effectively excluded via the --include_paths option.",
    )
    parser.add_argument(
        "--repo_path",
        type=str,
        dest="repo_path",
        default=None,
        help="Path to local repo clone. If provided, git_url will not be used",
    )
    parser.add_argument(
        "--cleanup",
        dest="cleanup",
        action="store_true",
        help="Clean up all temporary result files",
    )
    parser.add_argument(
        "git_url", nargs="?", type=str, help="repository URL for secret searching"
    )
    parser.add_argument(
        "--pre_commit",
        dest="pre_commit",
        action="store_true",
        help="Scan staged files in local repo clone",
    )
    args = parser.parse_args()
    rules = {}
    do_entropy = str2bool(args.do_entropy)
    do_regex = str2bool(args.do_regex)
    if not (do_entropy or do_regex):
        raise RuntimeError("no analysis requested")
    if do_regex and args.rules:
        try:
            with open(args.rules, "r") as rule_file:
                rules = json.loads(rule_file.read())
                for rule in rules:
                    rules[rule] = re.compile(rules[rule])
        except (IOError, ValueError):
            raise Exception("Error reading rules file")
        for regex in dict(regexes):
            del regexes[regex]
        for regex in rules:
            regexes[regex] = rules[regex]

    # read & compile path inclusion/exclusion patterns
    path_inclusions = []
    path_exclusions = []
    if args.include_paths:
        for pattern in set(l[:-1].lstrip() for l in args.include_paths):
            if pattern and not pattern.startswith("#"):
                path_inclusions.append(re.compile(pattern))
    if args.exclude_paths:
        for pattern in set(l[:-1].lstrip() for l in args.exclude_paths):
            if pattern and not pattern.startswith("#"):
                path_exclusions.append(re.compile(pattern))

    if args.pre_commit:
        output = find_staged(
            args.repo_path,
            args.output_json,
            do_regex,
            do_entropy,
            suppress_output=False,
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
        )
    else:
        if args.repo_path is None and args.git_url is None:
            raise SyntaxError("One of git_url or --repo_path is required")
        output = find_strings(
            args.git_url,
            args.since_commit,
            args.max_depth,
            args.output_json,
            do_regex,
            do_entropy,
            suppress_output=False,
            branch=args.branch,
            repo_path=args.repo_path,
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
        )
    if args.cleanup:
        clean_up(output)
    if output["found_issues"]:
        sys.exit(1)
    else:
        sys.exit(0)


def str2bool(v_string):
    if v_string is None:
        return True

    if v_string.lower() in ("yes", "true", "t", "y", "1"):
        return True

    if v_string.lower() in ("no", "false", "f", "n", "0"):
        return False

    raise argparse.ArgumentTypeError("Boolean value expected.")


BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
HEX_CHARS = "1234567890abcdefABCDEF"


# noinspection PyUnusedLocal
def del_rw(action, name, exc):  # pylint: disable=unused-argument
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def shannon_entropy(data, iterator):
    """
    Borrowed from http://blog.dkbza.org/2007/05/scanning-data-for-entropy-anomalies.html
    """
    if not data:
        return 0
    entropy = 0
    for inter_x in iterator:
        p_x = float(data.count(inter_x)) / len(data)
        if p_x > 0:
            entropy += -p_x * math.log(p_x, 2)
    return entropy


def get_strings_of_set(word, char_set, threshold=20):
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
        self.name = name


def clone_git_repo(git_url):
    project_path = tempfile.mkdtemp()
    Repo.clone_from(git_url, project_path)
    return project_path


def print_results(print_json, issue):
    if print_json:
        print(json.dumps(issue, sort_keys=True))
    else:
        printable_diff = issue["printDiff"]
        for string in issue["strings_found"]:
            printable_diff = printable_diff.replace(
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
        entropic_diff = {}
        entropic_diff["strings_found"] = strings_found
        entropic_diff["reason"] = "High Entropy"
        return [entropic_diff]
    return []


def find_regex(printable_diff, regex_list=None):
    if regex_list is None:
        regex_list = regexes
    regex_matches = []
    for key in regex_list:
        found_strings = regex_list[key].findall(printable_diff)
        if found_strings:
            found_regex = {}
            found_regex["strings_found"] = found_strings
            found_regex["reason"] = key
            regex_matches.append(found_regex)
    return regex_matches


def diff_worker(
    diff,
    custom_regexes,
    do_entropy,
    do_regex,
    print_json,
    suppress_output,
    path_inclusions,
    path_exclusions,
    prev_commit=None,
    branch_name=None,
):
    issues = []
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
            commit_time = None
        found_issues = []
        if do_entropy:
            found_issues = find_entropy(printable_diff)
        if do_regex:
            found_issues += find_regex(printable_diff, custom_regexes)
        for finding in found_issues:
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
    for found_issue in found_issues:
        result_path = os.path.join(output_dir, str(uuid.uuid4()))
        with open(result_path, "w+") as result_file:
            result_file.write(json.dumps(found_issue))
        output["found_issues"].append(result_path)
    return output


def path_included(blob, include_patterns=None, exclude_patterns=None):
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


# pylint: disable=too-many-arguments
def find_strings(
    git_url,
    since_commit=None,
    max_depth=1000000,
    print_json=False,
    do_regex=False,
    do_entropy=True,
    suppress_output=True,
    custom_regexes=None,
    branch=None,
    repo_path=None,
    path_inclusions=None,
    path_exclusions=None,
):
    output = {"found_issues": []}
    if repo_path:
        project_path = repo_path
    else:
        project_path = clone_git_repo(git_url)
    repo = Repo(project_path)
    already_searched = set()
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
            if not prev_commit:
                prev_commit = curr_commit
                continue
            elif diff_hash in already_searched:
                prev_commit = curr_commit
                continue
            else:
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
        diff = curr_commit.diff(NULL_TREE, create_patch=True)
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
        shutil.rmtree(project_path, onerror=del_rw)
    return output


def find_staged(
    project_path,
    print_json=False,
    do_regex=False,
    do_entropy=True,
    suppress_output=True,
    custom_regexes=None,
    path_inclusions=None,
    path_exclusions=None,
):
    output = {"found_issues": []}
    output_dir = tempfile.mkdtemp()
    repo = Repo(project_path, search_parent_directories=True)
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


def clean_up(output):
    print("Whhaat")
    issues_path = output.get("issues_path", None)
    if issues_path and os.path.isdir(issues_path):
        shutil.rmtree(output["issues_path"])


if __name__ == "__main__":
    main()
