# -*- coding: utf-8 -*-

import abc
import datetime
import hashlib
import math
import pathlib
from functools import lru_cache
from typing import cast, Dict, Generator, Iterable, List, Optional, Pattern, Set, Tuple

import git
import toml

from tartufo import config, util
from tartufo.types import GitOptions, GlobalOptions, IssueType, Chunk


BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
HEX_CHARS = "1234567890abcdefABCDEF"


class Issue:
    """Represents an issue found while scanning the code."""

    OUTPUT_SEPARATOR: str = "~~~~~~~~~~~~~~~~~~~~~"
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    issue_type: Optional[IssueType] = None
    issue_detail: Optional[str] = None
    diff: Optional[git.Diff] = None
    matched_string: str = ""
    commit: Optional[git.Commit] = None
    branch_name: Optional[str] = None

    def __init__(self, issue_type: IssueType, matched_string: str) -> None:
        self.issue_type = issue_type
        self.matched_string = matched_string

    def as_dict(self) -> Dict[str, Optional[str]]:
        """Return a dictionary representation of an issue.

        This is primarily meant to aid in JSON serialization.
        """
        output = {
            "issue_type": self.issue_type.value,  # type: ignore
            "issue_detail": self.issue_detail,
            "diff": self.printable_diff,
            "matched_string": self.matched_string,
            "signature": self.signature,
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

    @property
    def signature(self) -> Optional[str]:
        if self.file_path:
            return util.generate_signature(self.matched_string, self.file_path)
        return None

    def __str__(self) -> str:
        output = []
        diff_body = self.printable_diff
        diff_body = diff_body.replace(
            self.matched_string, util.style_warning(self.matched_string)
        )
        output.append(self.OUTPUT_SEPARATOR)
        output.append(util.style_ok("Reason: {}".format(self.issue_type.value)))  # type: ignore
        if self.issue_detail:
            output.append(util.style_ok("Detail: {}".format(self.issue_detail)))
        if self.file_path:
            output.append(util.style_ok("Filepath: {}".format(self.file_path)))
        if self.signature:
            output.append(util.style_ok("Signature: {}".format(self.signature)))
        if self.branch_name:
            output.append(util.style_ok("Branch: {}".format(self.branch_name)))
        if self.commit:
            output.append(util.style_ok("Date: {}".format(self.commit_time)))
            output.append(util.style_ok("Hash: {}".format(self.commit_hash)))
            output.append(util.style_ok("Commit: {}".format(self.commit_message)))

        output.append(diff_body)
        output.append(self.OUTPUT_SEPARATOR)
        return "\n".join(output)


class ScannerBase(abc.ABC):
    _issues: List[Issue]
    _included_paths: Optional[List[Pattern]] = None
    _excluded_paths: Optional[List[Pattern]] = None
    _rules_regexes: Optional[Dict[str, Pattern]] = None
    options: GlobalOptions

    def __init__(self, options: GlobalOptions) -> None:
        self.options = options

    @property
    def issues(self) -> List[Issue]:
        if not self._issues:
            self._issues = self.scan()
        return self._issues

    @property
    def included_paths(self) -> List[Pattern]:
        if self._included_paths is None:
            if self.options.include_paths:
                self._included_paths = config.compile_path_rules(
                    self.options.include_paths.readlines()
                )
            else:
                self._included_paths = []
        return self._included_paths

    @property
    def excluded_paths(self) -> List[Pattern]:
        if self._excluded_paths is None:
            if self.options.exclude_paths:
                self._excluded_paths = config.compile_path_rules(
                    self.options.exclude_paths.readlines()
                )
            else:
                self._excluded_paths = []
        return self._excluded_paths

    @property
    def rules_regexes(self):
        if self._rules_regexes is None:
            self._rules_regexes = config.configure_regexes(
                self.options.default_regexes,
                self.options.rules,
                self.options.git_rules_repo,
                self.options.git_rules_files,
            )
        return self._rules_regexes

    @lru_cache()
    def should_scan(self, file_path):
        """Check if the a file path should included in analysis.

        If non-empty, `self.included_paths` has precedence over
        `self.excluded_paths`, such that a file path that is not matched by any
        of the defined `self.included_paths` will be excluded, even when it is
        not matched by any of the defined `self.excluded_paths`. If either
        `self.included_pats` or `self.excluded_paths` are undefined or empty,
        they will have no effect, respectively. All file paths are included by
        this function when no inclusions or exclusions exist.

        :param file_path: The file path to check for inclusion
        :return: False if the file path is _not_ matched by `self.indluded_paths`
            (when non-empty) or if it is matched by `self.excluded_paths` (when
            non-empty), otherwise returns True
        """
        if self.included_paths and not any(
            p.match(file_path) for p in self.included_paths
        ):
            return False
        if self.excluded_paths and any(p.match(file_path) for p in self.excluded_paths):
            return False
        return True

    def signature_is_excluded(self, blob: str, file_path: str) -> bool:
        return (
            util.generate_signature(blob, file_path) in self.options.exclude_signatures
        )

    @lru_cache()
    def calculate_entropy(self, data: str, char_set: str) -> float:
        """
        Borrowed from http://blog.dkbza.org/2007/05/scanning-data-for-entropy-anomalies.html
        """
        if not data:
            return 0.0
        entropy = 0.0
        for char in char_set:
            prob_x = float(data.count(char)) / len(data)
            if prob_x > 0:
                entropy += -prob_x * math.log2(prob_x)
        return entropy

    def scan(self) -> List[Issue]:
        issues: List[Issue] = []
        for chunk in self.chunks:
            if self.options.entropy:
                issues += self.scan_entropy(chunk)
            if self.options.regex:
                issues += self.scan_regex(chunk)
        return issues

    def scan_entropy(self, chunk: Chunk) -> List[Issue]:
        issues: List[Issue] = []
        for line in chunk.contents.split("\n"):
            for word in line.split():
                b64_strings = util.get_strings_of_set(word, BASE64_CHARS)
                hex_strings = util.get_strings_of_set(word, HEX_CHARS)

                for string in b64_strings:
                    if not self.signature_is_excluded(string, chunk.file_path):
                        b64_entropy = self.calculate_entropy(string, BASE64_CHARS)
                        if b64_entropy > 4.5:
                            issues.append(Issue(IssueType.Entropy, string))

                for string in hex_strings:
                    if not self.signature_is_excluded(string, chunk.file_path):
                        hex_entropy = self.calculate_entropy(string, HEX_CHARS)
                        if hex_entropy > 3:
                            issues.append(Issue(IssueType.Entropy, string))
        return issues

    def scan_regex(self, chunk: Chunk) -> List[Issue]:
        issues: List[Issue] = []
        for key, pattern in self.rules_regexes:
            found_strings = pattern.findall(chunk.contents)
            for match in found_strings:
                # Filter out any explicitly "allowed" match signatures
                if self.signature_is_excluded(match, chunk.file_path):
                    issue = Issue(IssueType.RegEx, match)
                    issue.issue_detail = key
                    issues.append(issue)
        return issues

    @abc.abstractproperty
    def chunks(self) -> Generator[Chunk, None, None]:
        """Yield "chunks" of data to be scanned.

        Examples of "chunks" would be individual git commit diffs, or the
        contents of individual files.
        """


class GitRepoScanner(ScannerBase):
    __repo: git.Repo
    options: GitOptions

    def __init__(  # pylint: disable=super-init-not-called
        self, options: GitOptions, repo_path: str
    ) -> None:
        self.options = options
        self.repo_path = repo_path
        self.load_repo(self.repo_path)

    def load_repo(self, repo_path: str):
        self.__repo = git.Repo(repo_path)

    def _iter_diff_index(
        self, diff_index: git.DiffIndex
    ) -> Generator[Tuple[str, str], None, None]:
        diff: git.Diff
        for diff in diff_index:
            printable_diff: str = diff.diff.decode("utf-8", errors="replace")
            if printable_diff.startswith("Binary files"):
                continue
            file_path = diff.b_path if diff.b_path else diff.a_path
            if self.should_scan(file_path):
                yield (printable_diff, file_path)

    def _iter_branch_commits(
        self, repo: git.Repo, branch: git.FetchInfo
    ) -> Generator[Tuple[git.Commit, git.Commit], None, None]:
        since_commit_reached: bool = False
        prev_commit: git.Commit = None
        curr_commit: git.Commit = None

        for curr_commit in repo.iter_commits(
            branch.name, max_count=self.options.max_depth
        ):
            commit_hash = curr_commit.hexsha
            if self.options.since_commit:
                if commit_hash == self.options.since_commit:
                    since_commit_reached = True
                if since_commit_reached:
                    prev_commit = curr_commit
                    continue
            if not prev_commit:
                prev_commit = curr_commit
                continue
            yield (curr_commit, prev_commit)
            prev_commit = curr_commit

    @property
    def chunks(self) -> Generator[Chunk, None, None]:
        already_searched: Set[bytes] = set()

        if self.options.branch:
            branches = self.__repo.remotes.origin.fetch(self.options.branch)
        else:
            branches = self.__repo.remotes.origin.fetch()

        for remote_branch in branches:
            diff_index: git.DiffIndex = None
            diff_hash: bytes
            curr_commit: git.Commit = None
            prev_commit: git.Commit = None

            for curr_commit, prev_commit in self._iter_branch_commits(
                self.__repo, remote_branch
            ):
                diff_index = curr_commit.diff(prev_commit, create_patch=True)
                diff_hash = hashlib.md5(
                    (str(prev_commit) + str(curr_commit)).encode("utf-8")
                ).digest()
                if diff_hash in already_searched:
                    continue
                already_searched.add(diff_hash)
                for blob, file_path in self._iter_diff_index(diff_index):
                    yield Chunk(
                        blob,
                        file_path,
                        util.extract_commit_metadata(prev_commit, remote_branch),
                    )

            # Finally, yield the first commit to the branch
            diff = diff_index.diff(git.NULL_TREE, create_patch=True)
            for blob, file_path in self._iter_diff_index(diff):
                yield Chunk(
                    blob,
                    file_path,
                    util.extract_commit_metadata(prev_commit, remote_branch),
                )


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


def find_entropy(printable_diff: str) -> List[Issue]:
    issues = []
    lines = printable_diff.split("\n")
    for line in lines:
        for word in line.split():
            base64_strings = get_strings_of_set(word, BASE64_CHARS)
            hex_strings = get_strings_of_set(word, HEX_CHARS)
            for string in base64_strings:
                b64_entropy = shannon_entropy(string, BASE64_CHARS)
                if b64_entropy > 4.5:
                    issues.append(Issue(IssueType.Entropy, string))
            for string in hex_strings:
                hex_entropy = shannon_entropy(string, HEX_CHARS)
                if hex_entropy > 3:
                    issues.append(Issue(IssueType.Entropy, string))
    return issues


def find_regex(
    printable_diff: str, regex_list: Optional[Dict[str, Pattern]] = None
) -> List[Issue]:
    if regex_list is None:
        regex_list = {}
    regex_matches = []
    for key in regex_list:
        found_strings = regex_list[key].findall(printable_diff)
        for found in found_strings:
            issue = Issue(IssueType.RegEx, found)
            issue.issue_detail = key
            regex_matches.append(issue)
    return regex_matches


def diff_worker(
    diff: git.DiffIndex,
    options: GitOptions,
    custom_regexes: Optional[Dict[str, Pattern]],
    path_inclusions: Optional[Iterable[Pattern]],
    path_exclusions: Optional[Iterable[Pattern]],
    prev_commit: Optional[git.Commit] = None,
    branch_name: Optional[str] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    for blob in diff:
        printable_diff = blob.diff.decode("utf-8", errors="replace")
        if printable_diff.startswith("Binary files"):
            continue
        if not path_included(blob, path_inclusions, path_exclusions):
            continue
        found_issues: List[Issue] = []
        if options.entropy:
            found_issues += find_entropy(printable_diff)
        if options.regex:
            found_issues += find_regex(printable_diff, custom_regexes)
        for finding in found_issues:
            finding.diff = blob
            finding.commit = prev_commit
            finding.branch_name = branch_name
        issues += found_issues
    issues = list(
        filter(lambda x: x.signature not in options.exclude_signatures, issues)
    )
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
    options: GitOptions,
    custom_regexes: Optional[Dict[str, Pattern]] = None,
    path_inclusions: Optional[Iterable[Pattern]] = None,
    path_exclusions: Optional[Iterable[Pattern]] = None,
) -> List[Issue]:
    repo = git.Repo(repo_path)
    already_searched: Set[bytes] = set()
    all_issues: List[Issue] = []

    if options.branch:
        branches = repo.remotes.origin.fetch(options.branch)
    else:
        branches = repo.remotes.origin.fetch()

    for remote_branch in branches:
        since_commit_reached = False
        branch_name = remote_branch.name
        prev_commit = None
        curr_commit = None
        commit_hash = None
        for curr_commit in repo.iter_commits(branch_name, max_count=options.max_depth):
            commit_hash = curr_commit.hexsha
            if commit_hash == options.since_commit:
                since_commit_reached = True
            if options.since_commit and since_commit_reached:
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
                diff=diff,
                options=options,
                custom_regexes=custom_regexes,
                path_inclusions=path_inclusions,
                path_exclusions=path_exclusions,
                prev_commit=prev_commit,
                branch_name=branch_name,
            )
            all_issues.extend(found_issues)
            prev_commit = curr_commit
        # Handling the first commit
        diff = curr_commit.diff(git.NULL_TREE, create_patch=True)
        found_issues = diff_worker(
            diff=diff,
            options=options,
            custom_regexes=custom_regexes,
            path_inclusions=path_inclusions,
            path_exclusions=path_exclusions,
            prev_commit=prev_commit,
            branch_name=branch_name,
        )
        all_issues.extend(found_issues)
    return all_issues


def scan_repo(
    repo_path: str,
    regexes: Optional[Dict[str, Pattern]],
    path_inclusions: List[Pattern],
    path_exclusions: List[Pattern],
    options: GitOptions,
) -> List[Issue]:
    # Check the repo for any local configs
    repo_config: Dict[str, config.OptionTypes] = {}
    path = pathlib.Path(repo_path)
    config_file = path / "pyproject.toml"
    if not config_file.is_file():
        config_file = path / "tartufo.toml"
    if config_file.is_file() and str(config_file.resolve()) != str(options.config):
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
        repo_path=repo_path,
        options=options,
        custom_regexes=regexes,
        path_inclusions=path_inclusions,
        path_exclusions=path_exclusions,
    )


def find_staged(
    project_path: str,
    options: GitOptions,
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
        diff=diff,
        custom_regexes=custom_regexes,
        path_inclusions=path_inclusions,
        path_exclusions=path_exclusions,
        options=options,
    )
