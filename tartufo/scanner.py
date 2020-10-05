# -*- coding: utf-8 -*-

import abc
import hashlib
import math
import pathlib
import re
from functools import lru_cache
from typing import (
    Any,
    Dict,
    Generator,
    List,
    MutableMapping,
    Optional,
    Pattern,
    Set,
    Tuple,
)

import git

from tartufo import config, types, util


BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
HEX_CHARS = "1234567890abcdefABCDEF"


class Issue:
    """Represent an issue found while scanning a target."""

    OUTPUT_SEPARATOR: str = "~~~~~~~~~~~~~~~~~~~~~"

    chunk: types.Chunk
    issue_type: types.IssueType
    issue_detail: Optional[str] = None
    matched_string: str = ""

    def __init__(
        self, issue_type: types.IssueType, matched_string: str, chunk: types.Chunk
    ) -> None:
        """
        :param issue_type: What type of scan identified this issue
        :param matched_string: The string that was identified as a potential issue
        :param chunk: The chunk of data where the match was found
        """
        self.issue_type = issue_type
        self.matched_string = matched_string
        self.chunk = chunk

    def as_dict(self) -> Dict[str, Optional[str]]:
        """Return a dictionary representation of an issue.

        This is primarily meant to aid in JSON serialization.

        :return: A JSON serializable dictionary representation of this issue
        """
        return {
            "file_path": str(self.chunk.file_path),
            "matched_string": self.matched_string,
            "diff": self.chunk.contents,
            "signature": self.signature,
            "issue_type": self.issue_type.value,
            "issue_detail": self.issue_detail,
            **self.chunk.metadata,
        }

    @property
    def signature(self) -> str:
        """Generate a stable hash-based signature uniquely identifying this issue.

        :rtype: str
        """
        return util.generate_signature(self.matched_string, self.chunk.file_path)

    def __str__(self) -> str:
        output = []
        diff_body = self.chunk.contents
        diff_body = diff_body.replace(
            self.matched_string, util.style_warning(self.matched_string)
        )
        output.append(self.OUTPUT_SEPARATOR)
        output.append(util.style_ok("Reason: {}".format(self.issue_type.value)))  # type: ignore
        if self.issue_detail:
            output.append(util.style_ok("Detail: {}".format(self.issue_detail)))
        output.append(util.style_ok("Filepath: {}".format(self.chunk.file_path)))
        output.append(util.style_ok("Signature: {}".format(self.signature)))
        output += [
            util.style_ok("{}: {}".format(k.replace("_", " ").capitalize(), v))
            for k, v in self.chunk.metadata.items()
        ]

        output.append(diff_body)
        output.append(self.OUTPUT_SEPARATOR)
        return "\n".join(output)


class ScannerBase(abc.ABC):
    """Provide the base, generic functionality needed by all scanners.

    In fact, this contains all of the actual scanning logic. This part of the
    application should never differ; the part that differs, and the part that is
    left abstract here, is what content is provided to the various scans. For
    this reason, the `chunks` property is left abstract. It is up to the various
    scanners to implement this property, in the form of a generator, to yield
    all the individual pieces of content to be scanned.
    """

    _issues: Optional[List[Issue]] = None
    _included_paths: Optional[List[Pattern]] = None
    _excluded_paths: Optional[List[Pattern]] = None
    _rules_regexes: Optional[Dict[str, Pattern]] = None
    global_options: types.GlobalOptions

    def __init__(self, options: types.GlobalOptions) -> None:
        self.global_options = options

    @property
    def issues(self) -> List[Issue]:
        """Get a list of issues found during the scan.

        If a scan has not yet been run, run it.

        :return: Any issues found during the scan.
        :rtype: List[Issue]
        """
        if self._issues is None:
            self._issues = self.scan()
        return self._issues

    @property
    def included_paths(self) -> List[Pattern]:
        """Get a list of regexes used as an exclusive list of paths to scan.

        :rtype: List[Pattern]
        """
        if self._included_paths is None:
            if self.global_options.include_paths:
                self._included_paths = config.compile_path_rules(
                    self.global_options.include_paths.readlines()
                )
                self.global_options.include_paths.close()
            else:
                self._included_paths = []
        return self._included_paths

    @property
    def excluded_paths(self) -> List[Pattern]:
        """Get a list of regexes used to match paths to exclude from the scan.

        :rtype: List[Pattern]
        """
        if self._excluded_paths is None:
            if self.global_options.exclude_paths:
                self._excluded_paths = config.compile_path_rules(
                    self.global_options.exclude_paths.readlines()
                )
                self.global_options.exclude_paths.close()
            else:
                self._excluded_paths = []
        return self._excluded_paths

    @property
    def rules_regexes(self) -> Dict[str, Pattern]:
        """Get a dictionary of regular expressions to scan the code for.

        :raises types.TartufoConfigException: If there was a problem compiling the rules
        :rtype: Dict[str, Pattern]
        """
        if self._rules_regexes is None:
            try:
                self._rules_regexes = config.configure_regexes(
                    self.global_options.default_regexes,
                    self.global_options.rules,
                    self.global_options.git_rules_repo,
                    self.global_options.git_rules_files,
                )
            except (ValueError, re.error) as exc:
                raise types.ConfigException(str(exc)) from exc
        return self._rules_regexes

    @lru_cache()
    def should_scan(self, file_path: str):
        """Check if the a file path should be included in analysis.

        If non-empty, `self.included_paths` has precedence over
        `self.excluded_paths`, such that a file path that is not matched by any
        of the defined `self.included_paths` will be excluded, even when it is
        not matched by any of the defined `self.excluded_paths`. If either
        `self.included_paths` or `self.excluded_paths` are undefined or empty,
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
        """Find whether the signature of some data has been excluded in configuration.

        :param blob: The piece of data which is being scanned
        :param file_path: The path and file name for the data being scanned
        """
        return (
            util.generate_signature(blob, file_path)
            in self.global_options.exclude_signatures
        )

    @lru_cache()
    def calculate_entropy(self, data: str, char_set: str) -> float:
        """Calculate the Shannon entropy for a piece of data.

        This essentially calculates the overall probability for each character
        in `data` to be to be present, based on the characters in `char_set`.
        By doing this, we can tell how random a string appears to be.

        Borrowed from http://blog.dkbza.org/2007/05/scanning-data-for-entropy-anomalies.html

        :param data: The data to be scanned for its entropy
        :param char_set: The character set used as a basis for the calculation
        :return: The amount of entropy detected in the data.
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
        """Run the requested scans against the target data.

        This will iterate through all chunks of data as provided by the scanner
        implementation, and run all requested scans against it, as specified in
        `self.global_options`.

        :raises types.TartufoConfigException: If there were problems with the
          scanner's configuration
        """
        issues: List[Issue] = []
        if not any((self.global_options.entropy, self.global_options.regex)):
            raise types.ConfigException("No analysis requested.")
        if self.global_options.regex and not self.rules_regexes:
            raise types.ConfigException("Regex checks requested, but no regexes found.")

        for chunk in self.chunks:
            # Run regex scans first to trigger a potential fast fail for bad config
            if self.global_options.regex and self.rules_regexes:
                issues += self.scan_regex(chunk)
            if self.global_options.entropy:
                issues += self.scan_entropy(chunk)
        self._issues = issues
        return self._issues

    def scan_entropy(self, chunk: types.Chunk) -> List[Issue]:
        """Scan a chunk of data for apparent high entropy.

        :param chunk: The chunk of data to be scanned
        """
        issues: List[Issue] = []
        for line in chunk.contents.split("\n"):
            for word in line.split():
                b64_strings = util.get_strings_of_set(word, BASE64_CHARS)
                hex_strings = util.get_strings_of_set(word, HEX_CHARS)

                for string in b64_strings:
                    if not self.signature_is_excluded(string, chunk.file_path):
                        b64_entropy = self.calculate_entropy(string, BASE64_CHARS)
                        if b64_entropy > 4.5:
                            issues.append(Issue(types.IssueType.Entropy, string, chunk))

                for string in hex_strings:
                    if not self.signature_is_excluded(string, chunk.file_path):
                        hex_entropy = self.calculate_entropy(string, HEX_CHARS)
                        if hex_entropy > 3:
                            issues.append(Issue(types.IssueType.Entropy, string, chunk))
        return issues

    def scan_regex(self, chunk: types.Chunk) -> List[Issue]:
        """Scan a chunk of data for matches against the configured regexes.

        :param chunk: The chunk of data to be scanned
        """
        issues: List[Issue] = []
        for key, pattern in self.rules_regexes.items():
            found_strings = pattern.findall(chunk.contents)
            for match in found_strings:
                # Filter out any explicitly "allowed" match signatures
                if not self.signature_is_excluded(match, chunk.file_path):
                    issue = Issue(types.IssueType.RegEx, match, chunk)
                    issue.issue_detail = key
                    issues.append(issue)
        return issues

    @property
    @abc.abstractmethod
    def chunks(self) -> Generator[types.Chunk, None, None]:
        """Yield "chunks" of data to be scanned.

        Examples of "chunks" would be individual git commit diffs, or the
        contents of individual files.

        :rtype: Generator[Chunk, None, None]
        """


class GitScanner(ScannerBase, abc.ABC):
    """A base class for scanners looking at git history.

    This is a lightweight base class to provide some basic functionality needed
    across all scanner that are interacting with git history.
    """

    _repo: git.Repo
    repo_path: str

    def __init__(self, global_options: types.GlobalOptions, repo_path: str) -> None:
        """
        :param global_options: The options provided to the top-level tartufo command
        :param repo_path: The local filesystem path pointing to the repository
        """
        self.repo_path = repo_path
        super().__init__(global_options)
        self._repo = self.load_repo(self.repo_path)

    def _iter_diff_index(
        self, diff_index: git.DiffIndex
    ) -> Generator[Tuple[str, str], None, None]:
        """Iterate over a "diff index", yielding the individual file changes.

        A "diff index" is essentially analogous to a single commit in the git
        history. So what this does is iterate over a single commit, and yield
        the changes to each individual file in that commit, along with its file
        path. This will also check the file path and ensure that it has not been
        excluded from the scan by configuration.

        Note that binary files are wholly skipped.

        :param diff_index: The diff index / commit to be iterated over
        """
        diff: git.Diff
        for diff in diff_index:
            printable_diff: str = diff.diff.decode("utf-8", errors="replace")
            if printable_diff.startswith("Binary files"):
                continue
            file_path = diff.b_path if diff.b_path else diff.a_path
            if self.should_scan(file_path):
                yield (printable_diff, file_path)

    @abc.abstractmethod
    def load_repo(self, repo_path: str) -> git.Repo:
        """Load and return the repository to be scanned.

        :param repo_path: The local filesystem path pointing to the repository
        :raises types.GitLocalException: If there was a problem loading the repository
        """


class GitRepoScanner(GitScanner):

    git_options: types.GitOptions

    def __init__(
        self,
        global_options: types.GlobalOptions,
        git_options: types.GitOptions,
        repo_path: str,
    ) -> None:
        """Used for scanning a full clone of a git repository.

        :param global_options: The options provided to the top-level tartufo command
        :param git_options: The options specific to interacting with a git repository
        :param repo_path: The local filesystem path pointing to the repository
        """
        self.git_options = git_options
        super().__init__(global_options, repo_path)

    def load_repo(self, repo_path: str) -> git.Repo:
        config_file: Optional[pathlib.Path] = None
        data: MutableMapping[str, Any] = {}
        try:
            (config_file, data) = config.load_config_from_path(
                pathlib.Path(repo_path), traverse=False
            )
        except (FileNotFoundError, types.ConfigException) as exc:
            config_file = None
        if config_file and config_file != self.global_options.config:
            signatures = data.get("exclude_signatures", None)
            if signatures:
                self.global_options.exclude_signatures = tuple(
                    set(self.global_options.exclude_signatures + tuple(signatures))
                )
            extras_path = data.get("include_paths", None)
            if extras_path:
                extras_file = pathlib.Path(repo_path, extras_path)
                if extras_file.exists():
                    includes = self.included_paths
                    with extras_file.open() as handle:
                        includes += config.compile_path_rules(handle.readlines())
                    self._included_paths = includes
            extras_path = data.get("exclude_paths", None)
            if extras_path:
                extras_file = pathlib.Path(repo_path, extras_path)
                if extras_file.exists():
                    excludes = self.excluded_paths
                    with extras_file.open() as handle:
                        excludes += config.compile_path_rules(handle.readlines())
                    self._excluded_paths = excludes
        try:
            return git.Repo(repo_path)
        except git.GitError as exc:
            raise types.GitLocalException(str(exc)) from exc

    def _iter_branch_commits(
        self, repo: git.Repo, branch: git.FetchInfo
    ) -> Generator[Tuple[git.Commit, git.Commit], None, None]:
        """Iterate over and yield the commits on a branch.

        :param repo: The repository from which to extract the branch and commits
        :param branch: The branch to iterate over
        """
        since_commit_reached: bool = False
        prev_commit: git.Commit = None
        curr_commit: git.Commit = None

        for curr_commit in repo.iter_commits(
            branch.name, max_count=self.git_options.max_depth
        ):
            commit_hash = curr_commit.hexsha
            if self.git_options.since_commit:
                if commit_hash == self.git_options.since_commit:
                    since_commit_reached = True
                if since_commit_reached:
                    prev_commit = curr_commit
                    break
            if not prev_commit:
                prev_commit = curr_commit
                continue
            yield (curr_commit, prev_commit)
            prev_commit = curr_commit

    @property
    def chunks(self) -> Generator[types.Chunk, None, None]:
        """Yield individual diffs from the repository's history.

        :rtype: Generator[Chunk, None, None]
        :raises types.GitRemoteException: If there was an error fetching branches
        """
        already_searched: Set[bytes] = set()

        try:
            if self.git_options.branch:
                branches = self._repo.remotes.origin.fetch(self.git_options.branch)
            else:
                branches = self._repo.remotes.origin.fetch()
        except git.GitCommandError as exc:
            raise types.GitRemoteException(exc.stderr.strip()) from exc

        for remote_branch in branches:
            diff_index: git.DiffIndex = None
            diff_hash: bytes
            curr_commit: git.Commit = None
            prev_commit: git.Commit = None

            for curr_commit, prev_commit in self._iter_branch_commits(
                self._repo, remote_branch
            ):
                diff_index = curr_commit.diff(prev_commit, create_patch=True)
                diff_hash = hashlib.md5(
                    (str(prev_commit) + str(curr_commit)).encode("utf-8")
                ).digest()
                if diff_hash in already_searched:
                    continue
                already_searched.add(diff_hash)
                for blob, file_path in self._iter_diff_index(diff_index):
                    yield types.Chunk(
                        blob,
                        file_path,
                        util.extract_commit_metadata(prev_commit, remote_branch),
                    )

            # Finally, yield the first commit to the branch
            if curr_commit:
                diff = curr_commit.diff(git.NULL_TREE, create_patch=True)
                for blob, file_path in self._iter_diff_index(diff):
                    yield types.Chunk(
                        blob,
                        file_path,
                        util.extract_commit_metadata(prev_commit, remote_branch),
                    )


class GitPreCommitScanner(GitScanner):
    """For use in a git pre-commit hook."""

    def load_repo(self, repo_path: str) -> git.Repo:
        return git.Repo(repo_path, search_parent_directories=True)

    @property
    def chunks(self):
        """Yield the individual file changes currently staged for commit.

        :rtype: Generator[Chunk, None, None]
        """
        diff_index = self._repo.index.diff(
            self._repo.head.commit, create_patch=True, R=True
        )
        for blob, file_path in self._iter_diff_index(diff_index):
            yield types.Chunk(blob, file_path)
