# -*- coding: utf-8 -*-

import datetime
import enum
import hashlib
import math
import pathlib
from typing import cast, Dict, Iterable, List, Optional, Pattern, Set

import git
import toml
from tartufo import config
from tartufo.util import style_ok, style_warning


BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
HEX_CHARS = "1234567890abcdefABCDEF"


class IssueType(enum.Enum):
    Entropy = "High Entropy"
    RegEx = "Regular Expression Match"


class Issue:
    """Represents an issue found while scanning the code."""

    OUTPUT_SEPARATOR = "~~~~~~~~~~~~~~~~~~~~~"  # type: str
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"  # type: str

    issue_type = None  # type: Optional[IssueType]
    issue_detail = None  # type: Optional[str]
    diff = None  # type: Optional[git.Diff]
    strings_found = None  # type: Optional[List[str]]
    commit = None  # type: Optional[git.Commit]
    branch_name = None  # type: Optional[str]

    def __init__(self, issue_type: IssueType, strings_found: List[str]) -> None:
        self.issue_type = issue_type
        self.strings_found = strings_found

    def as_dict(self) -> Dict[str, Optional[str]]:
        """Return a dictionary representation of an issue.

        This is primarily meant to aid in JSON serialization.
        """
        output = {
            "issue_type": self.issue_type.value,  # type: ignore
            "issue_detail": self.issue_detail,
            "diff": self.printable_diff,
            "strings_found": self.strings_found,
            "commit_time": self.commit_time,
            "commit_message": self.commit_message,
            "commit_hash": self.commit_hash,
            "file_path": self.file_path,
            "branch": self.branch_name,
        }
        return output

    @property
    def printable_diff(self) -> str:
        if not self.diff:
            return "No diff available."
        return self.diff.diff.decode("utf-8", errors="replace")

    @property
    def commit_time(self) -> Optional[str]:
        if not self.commit:
            return None
        commit_time = datetime.datetime.fromtimestamp(self.commit.committed_date)
        return commit_time.strftime(self.DATETIME_FORMAT)

    @property
    def commit_message(self) -> Optional[str]:
        if not self.commit:
            return None
        return self.commit.message

    @property
    def commit_hash(self) -> Optional[str]:
        if not self.commit:
            return None
        return self.commit.hexsha

    @property
    def file_path(self) -> Optional[str]:
        if not self.diff:
            return None
        if self.diff.b_path:
            return self.diff.b_path
        return self.diff.a_path

    def __str__(self) -> str:
        output = []
        diff_body = self.printable_diff
        for bad_str in self.strings_found:  # type: ignore
            diff_body = diff_body.replace(bad_str, style_warning(bad_str))
        output.append(self.OUTPUT_SEPARATOR)
        output.append(style_ok("Reason: {}".format(self.issue_type.value)))  # type: ignore
        if self.issue_detail:
            output.append(style_ok("Detail: {}".format(self.issue_detail)))
        if self.diff:
            output.append(style_ok("Filepath: {}".format(self.file_path)))
        if self.branch_name:
            output.append(style_ok("Branch: {}".format(self.branch_name)))
        if self.commit:
            output.append(style_ok("Date: {}".format(self.commit_time)))
            output.append(style_ok("Hash: {}".format(self.commit_hash)))
            output.append(style_ok("Commit: {}".format(self.commit_message)))

        output.append(diff_body)
        output.append(self.OUTPUT_SEPARATOR)
        return "\n".join(output)


def shannon_entropy(data: str, iterator: Iterable[str]) -> float:
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


def get_strings_of_set(
    word: str, char_set: Iterable[str], threshold: int = 20
) -> List[str]:
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


def find_entropy(printable_diff: str) -> Optional[Issue]:
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
        return Issue(IssueType.Entropy, strings_found)
    return None


def find_regex(
    printable_diff: str, regex_list: Optional[Dict[str, Pattern]] = None
) -> List[Issue]:
    if regex_list is None:
        regex_list = {}
    regex_matches = []
    for key in regex_list:
        found_strings = regex_list[key].findall(printable_diff)
        if found_strings:
            issue = Issue(IssueType.RegEx, found_strings)
            issue.issue_detail = key
            regex_matches.append(issue)
    return regex_matches


def diff_worker(
    diff: git.DiffIndex,
    custom_regexes: Optional[Dict[str, Pattern]],
    do_entropy: bool,
    do_regex: bool,
    path_inclusions: Optional[Iterable[Pattern]],
    path_exclusions: Optional[Iterable[Pattern]],
    prev_commit: Optional[git.Commit] = None,
    branch_name: Optional[str] = None,
) -> List[Issue]:
    issues = []  # type: List[Issue]
    for blob in diff:
        printable_diff = blob.diff.decode("utf-8", errors="replace")
        if printable_diff.startswith("Binary files"):
            continue
        if not path_included(blob, path_inclusions, path_exclusions):
            continue
        found_issues = []  # type: List[Issue]
        if do_entropy:
            entropy_issue = find_entropy(printable_diff)
            if entropy_issue:
                found_issues.append(entropy_issue)
        if do_regex:
            found_issues += find_regex(printable_diff, custom_regexes)
        for finding in found_issues:
            finding.diff = blob
            finding.commit = prev_commit
            finding.branch_name = branch_name
        issues += found_issues
    return issues


def path_included(
    blob: git.Blob,
    include_patterns: Optional[Iterable[Pattern]] = None,
    exclude_patterns: Optional[Iterable[Pattern]] = None,
) -> bool:
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
    repo_path: str,
    since_commit: Optional[str] = None,
    max_depth: int = 1000000,
    do_regex: bool = False,
    do_entropy: bool = True,
    custom_regexes: Optional[Dict[str, Pattern]] = None,
    branch: Optional[str] = None,
    path_inclusions: Optional[Iterable[Pattern]] = None,
    path_exclusions: Optional[Iterable[Pattern]] = None,
) -> List[Issue]:
    repo = git.Repo(repo_path)
    already_searched = set()  # type: Set[bytes]
    all_issues = []  # type: List[Issue]

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
            diff = curr_commit.diff(prev_commit, create_patch=True)
            # avoid searching the same diffs
            already_searched.add(diff_hash)
            found_issues = diff_worker(
                diff,
                custom_regexes,
                do_entropy,
                do_regex,
                path_inclusions,
                path_exclusions,
                prev_commit,
                branch_name,
            )
            all_issues.extend(found_issues)
            prev_commit = curr_commit
        # Handling the first commit
        diff = curr_commit.diff(git.NULL_TREE, create_patch=True)
        found_issues = diff_worker(
            diff,
            custom_regexes,
            do_entropy,
            do_regex,
            path_inclusions,
            path_exclusions,
            prev_commit,
            branch_name,
        )
        all_issues.extend(found_issues)
    return all_issues


def scan_repo(
    repo_path: str,
    regexes: Optional[Dict[str, Pattern]],
    path_inclusions: List[Pattern],
    path_exclusions: List[Pattern],
    options: Dict[str, config.OptionTypes],
) -> List[Issue]:
    # Check the repo for any local configs
    repo_config = {}  # type: Dict[str, config.OptionTypes]
    path = pathlib.Path(repo_path)
    config_file = path / "pyproject.toml"
    if not config_file.is_file():
        config_file = path / "tartufo.toml"
    if config_file.is_file() and str(config_file.resolve()) != str(options["config"]):
        toml_file = toml.load(str(config_file))
        repo_config = toml_file.get("tool", {}).get("tartufo", {})
    if repo_config:
        normalized_config = {
            k.replace("--", "").replace("-", "_"): v for k, v in repo_config.items()
        }
        extra_paths = cast(str, normalized_config.get("include_paths", None))
        if extra_paths:
            file_path = pathlib.Path(extra_paths).resolve()
            if file_path.is_file():
                with file_path.open("r", encoding="utf8") as paths_file:
                    path_inclusions.extend(
                        config.compile_path_rules(paths_file.readlines())
                    )
        extra_paths = cast(str, normalized_config.get("exclude_paths", None))
        if extra_paths:
            file_path = pathlib.Path(extra_paths).resolve()
            if file_path.is_file():
                with file_path.open("r", encoding="utf8") as paths_file:
                    path_exclusions.extend(
                        config.compile_path_rules(paths_file.readlines())
                    )

    return find_strings(
        repo_path,
        since_commit=cast(str, options["since_commit"]),
        max_depth=cast(int, options["max_depth"]),
        do_regex=cast(bool, options["regex"]),
        do_entropy=cast(bool, options["entropy"]),
        custom_regexes=regexes,
        branch=cast(str, options["branch"]),
        path_inclusions=path_inclusions,
        path_exclusions=path_exclusions,
    )


def find_staged(
    project_path: str,
    do_regex: bool = False,
    do_entropy: bool = True,
    custom_regexes: Optional[Dict[str, Pattern]] = None,
    path_inclusions: Optional[Iterable[Pattern]] = None,
    path_exclusions: Optional[Iterable[Pattern]] = None,
) -> List[Issue]:
    repo = git.Repo(project_path, search_parent_directories=True)
    # using "create_patch=True" below causes output list to be empty
    # unless "R=True" also is specified. See GitPython issue 852:
    # https://github.com/gitpython-developers/GitPython/issues/852
    diff = repo.index.diff(repo.head.commit, create_patch=True, R=True)
    return diff_worker(
        diff, custom_regexes, do_entropy, do_regex, path_inclusions, path_exclusions,
    )
