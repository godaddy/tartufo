# -*- coding: utf-8 -*-

import abc
from functools import lru_cache
import hashlib
import logging
import math
import pathlib
import re
import threading
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

import click
import git

import pygit2

from tartufo import config, types, util
from tartufo.types import BranchNotFoundException, Rule, TartufoException

BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
HEX_CHARS = "1234567890abcdefABCDEF"


class Issue:
    """Represent an issue found while scanning a target."""

    __slots__ = (
        "OUTPUT_SEPARATOR",
        "chunk",
        "issue_type",
        "issue_detail",
        "matched_string",
        "logger",
    )

    OUTPUT_SEPARATOR: str
    chunk: types.Chunk
    issue_type: types.IssueType
    issue_detail: Optional[str]
    matched_string: str
    logger: logging.Logger

    def __init__(
        self, issue_type: types.IssueType, matched_string: str, chunk: types.Chunk
    ) -> None:
        """
        :param issue_type: What type of scan identified this issue
        :param matched_string: The string that was identified as a potential issue
        :param chunk: The chunk of data where the match was found
        """
        self.OUTPUT_SEPARATOR = "~~~~~~~~~~~~~~~~~~~~~"  # pylint: disable=invalid-name
        self.issue_detail = None

        self.issue_type = issue_type
        self.matched_string = matched_string
        self.chunk = chunk
        self.logger = logging.getLogger(__name__)

    def as_dict(self, compact=False) -> Dict[str, Optional[str]]:
        """Return a dictionary representation of an issue.

        This is primarily meant to aid in JSON serialization.

        :compact: True to return a dictionary with fewer fields.
        :return: A JSON serializable dictionary representation of this issue
        """

        output = {
            "file_path": str(self.chunk.file_path),
            "matched_string": self.matched_string,
            "signature": self.signature,
            "issue_type": self.issue_type.value,
            "issue_detail": self.issue_detail,
        }
        if not compact:
            output.update({"diff": self.chunk.contents, **self.chunk.metadata})

        return output

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
        output.append(util.style_ok(f"Reason: {self.issue_type.value}"))  # type: ignore
        if self.issue_detail:
            output.append(util.style_ok(f"Detail: {self.issue_detail}"))
        output.append(util.style_ok(f"Filepath: {self.chunk.file_path}"))
        output.append(util.style_ok(f"Signature: {self.signature}"))
        output += [
            util.style_ok(f"{k.replace('_', ' ').capitalize()}: {v}")
            for k, v in self.chunk.metadata.items()
        ]

        output.append(diff_body)
        output.append(self.OUTPUT_SEPARATOR)
        return "\n".join(output)

    def __bytes__(self) -> bytes:
        return self.__str__().encode("utf8")


class ScannerBase(abc.ABC):  # pylint: disable=too-many-instance-attributes
    """Provide the base, generic functionality needed by all scanners.

    In fact, this contains all of the actual scanning logic. This part of the
    application should never differ; the part that differs, and the part that is
    left abstract here, is what content is provided to the various scans. For
    this reason, the `chunks` property is left abstract. It is up to the various
    scanners to implement this property, in the form of a generator, to yield
    all the individual pieces of content to be scanned.
    """

    _issues: List[Issue] = []
    _completed: bool = False
    _included_paths: Optional[List[Pattern]] = None
    _excluded_paths: Optional[List[Pattern]] = None
    _excluded_entropy: Optional[List[Rule]] = None
    _rules_regexes: Optional[Dict[str, Rule]] = None
    global_options: types.GlobalOptions
    logger: logging.Logger
    _scan_lock: threading.Lock = threading.Lock()

    def __init__(self, options: types.GlobalOptions) -> None:
        self.global_options = options
        self.logger = logging.getLogger(__name__)

    @property
    def completed(self) -> bool:
        """Return True if scan has completed

        :returns: True if scan has completed; False if scan is in progress
        """

        return self._completed

    @property
    def issues(self) -> List[Issue]:
        """Get a list of issues found during the scan.

        If the scan is still in progress, force it to complete first.

        :returns: Any issues found during the scan.
        """

        # Note there is no locking in this method (which is readonly). If the
        # first scan is not completed (or even if we mistakenly believe it is
        # not completed, due to a race), we call scan (which is protected) to
        # ensure the issues list is complete. By the time we reach the return
        # statement here, we know _issues is stable.

        if not self.completed:
            self.logger.debug(
                "Issues called before scan completed. Finishing scan now."
            )
            list(self.scan())

        return self._issues

    @property
    def included_paths(self) -> List[Pattern]:
        """Get a list of regexes used as an exclusive list of paths to scan.

        :rtype: List[Pattern]
        """
        if self._included_paths is None:
            self.logger.info("Initializing included paths")
            patterns = list(self.global_options.include_path_patterns or ())
            self._included_paths = (
                config.compile_path_rules(set(patterns)) if patterns else []
            )
            self.logger.debug(
                "Included paths was initialized as: %s", self._included_paths
            )
        return self._included_paths

    @property
    def excluded_entropy(self) -> List[Rule]:
        """Get a list of regexes used as an exclusive list of paths to scan.

        :rtype: List[Pattern]
        """
        if self._excluded_entropy is None:
            self.logger.info("Initializing excluded entropy patterns")
            patterns = list(self.global_options.exclude_entropy_patterns or ())
            self._excluded_entropy = config.compile_rules(patterns) if patterns else []
            self.logger.debug(
                "Excluded entropy was initialized as: %s", self._excluded_entropy
            )
        return self._excluded_entropy

    @property
    def excluded_paths(self) -> List[Pattern]:
        """Get a list of regexes used to match paths to exclude from the scan.

        :rtype: List[Pattern]
        """
        if self._excluded_paths is None:
            self.logger.info("Initializing excluded paths")
            patterns = list(self.global_options.exclude_path_patterns or ())
            self._excluded_paths = (
                config.compile_path_rules(set(patterns)) if patterns else []
            )
            self.logger.debug(
                "Excluded paths was initialized as: %s", self._excluded_paths
            )
        return self._excluded_paths

    @property
    def rules_regexes(self) -> Dict[str, Rule]:
        """Get a dictionary of regular expressions to scan the code for.

        :raises types.TartufoConfigException: If there was a problem compiling the rules
        :rtype: Dict[str, Pattern]
        """
        if self._rules_regexes is None:
            self.logger.info("Initializing regex rules")
            try:
                self._rules_regexes = config.configure_regexes(
                    self.global_options.default_regexes,
                    self.global_options.rules,
                    self.global_options.git_rules_repo,
                    self.global_options.git_rules_files,
                )
            except (ValueError, re.error) as exc:
                self.logger.exception("Error loading regex rules", exc_info=exc)
                raise types.ConfigException(str(exc)) from exc
            self.logger.debug(
                "Regex rules were initialized as: %s", self._rules_regexes
            )
        return self._rules_regexes

    @lru_cache(maxsize=None)
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
        :return: False if the file path is _not_ matched by `self.included_paths`
            (when non-empty) or if it is matched by `self.excluded_paths` (when
            non-empty), otherwise returns True
        """
        if self.included_paths and not any(
            p.match(file_path) for p in self.included_paths
        ):
            self.logger.info("%s excluded - did not match included paths", file_path)
            return False
        if self.excluded_paths and any(p.match(file_path) for p in self.excluded_paths):
            self.logger.info("%s excluded - matched excluded paths", file_path)
            return False
        return True

    def signature_is_excluded(self, blob: str, file_path: str) -> bool:
        """Find whether the signature of some data has been excluded in configuration.

        :param blob: The piece of data which is being scanned
        :param file_path: The path and file name for the data being scanned
        """
        return (
            blob
            in self.global_options.exclude_signatures  # Signatures themselves pop up as entropy matches
            or util.generate_signature(blob, file_path)
            in self.global_options.exclude_signatures
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def rule_matches(rule: Rule, string: str, line: str, path: str) -> bool:
        """
        Match string and path against rule.

        :param rule: Rule to perform match
        :param string: string to match against rule pattern
        :param path: path to match against rule path_pattern
        :return: True if string and path matched, False otherwise.
        """
        match = False
        if rule.re_match_type == "match":
            if rule.pattern:
                match = rule.pattern.match(string) is not None
            if rule.path_pattern:
                match = match and rule.path_pattern.match(path) is not None
        elif rule.re_match_type == "search":
            if rule.pattern:
                match = rule.pattern.search(line) is not None
            if rule.path_pattern:
                match = match and rule.path_pattern.search(path) is not None

        return match

    def entropy_string_is_excluded(self, string: str, line: str, path: str) -> bool:
        """Find whether the signature of some data has been excluded in configuration.

        :param string: String to check against rule pattern
        :param path: Path to check against rule path pattern
        :return: True if excluded, False otherwise
        """

        return bool(self.excluded_entropy) and any(
            ScannerBase.rule_matches(p, string, line, path)
            for p in self.excluded_entropy
        )

    @lru_cache(maxsize=None)
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

    def scan(self) -> Generator[Issue, None, None]:
        """Run the requested scans against the target data.

        This will iterate through all chunks of data as provided by the scanner
        implementation, and run all requested scans against it, as specified in
        `self.global_options`.

        The scan method is thread-safe; if multiple concurrent scans are requested,
        the first will run to completion while other callers are blocked (after
        which they will each execute in turn, yielding cached issues without
        repeating the underlying repository scan).

        :raises types.TartufoConfigException: If there were problems with the
          scanner's configuration
        """

        # I cannot find any written description of the python memory model. The
        # correctness of this code in multithreaded environments relies on the
        # expectation that the write to _completed at the bottom of the critical
        # section cannot be reordered to appear after the implicit release of
        # _scan_lock (when viewed from a competing thread).
        with self._scan_lock:
            if self._completed:
                yield from self._issues
                return

            if not any((self.global_options.entropy, self.global_options.regex)):
                self.logger.error("No analysis requested.")
                raise types.ConfigException("No analysis requested.")
            if self.global_options.regex and not self.rules_regexes:
                self.logger.error("Regex checks requested, but no regexes found.")
                raise types.ConfigException(
                    "Regex checks requested, but no regexes found."
                )

            self.logger.info("Starting scan...")
            self._issues = []
            for chunk in self.chunks:
                # Run regex scans first to trigger a potential fast fail for bad config
                if self.global_options.regex and self.rules_regexes:
                    for issue in self.scan_regex(chunk):
                        self._issues.append(issue)
                        yield issue
                if self.global_options.entropy:
                    for issue in self.scan_entropy(
                        chunk,
                        self.global_options.b64_entropy_score,
                        self.global_options.hex_entropy_score,
                    ):
                        self._issues.append(issue)
                        yield issue
            self._completed = True
            self.logger.info("Found %d issues.", len(self._issues))

    def scan_entropy(
        self, chunk: types.Chunk, b64_entropy_score: float, hex_entropy_score: float
    ) -> Generator[Issue, None, None]:
        """Scan a chunk of data for apparent high entropy.

        :param chunk: The chunk of data to be scanned
        :param b64_entropy_score: Base64 entropy score
        :param hex_entropy_score: Hexadecimal entropy score
        """

        for line in chunk.contents.split("\n"):
            for word in line.split():
                b64_strings = util.get_strings_of_set(word, BASE64_CHARS)
                hex_strings = util.get_strings_of_set(word, HEX_CHARS)

                for string in b64_strings:
                    yield from self.evaluate_entropy_string(
                        chunk, line, string, BASE64_CHARS, b64_entropy_score
                    )

                for string in hex_strings:
                    yield from self.evaluate_entropy_string(
                        chunk, line, string, HEX_CHARS, hex_entropy_score
                    )

    def evaluate_entropy_string(
        self,
        chunk: types.Chunk,
        line: str,
        string: str,
        chars: str,
        min_entropy_score: float,
    ) -> Generator[Issue, None, None]:
        """
        Check entropy string using entropy characters and score.

        :param chunk: The chunk of data to check
        :param issues: Issue list to append any strings flagged
        :param string: String to check
        :param chars: Characters to calculate score
        :param min_entropy_score: Minimum entropy score to flag
        return: Iterator of issues flagged
        """
        if not self.signature_is_excluded(string, chunk.file_path):
            entropy_score = self.calculate_entropy(string, chars)
            if entropy_score > min_entropy_score:
                if self.entropy_string_is_excluded(string, line, chunk.file_path):
                    self.logger.debug("line containing entropy was excluded: %s", line)
                else:
                    yield Issue(types.IssueType.Entropy, string, chunk)

    def scan_regex(self, chunk: types.Chunk) -> Generator[Issue, None, None]:
        """Scan a chunk of data for matches against the configured regexes.

        :param chunk: The chunk of data to be scanned
        """

        for key, rule in self.rules_regexes.items():
            if rule.path_pattern is None or rule.path_pattern.match(chunk.file_path):
                found_strings = rule.pattern.findall(chunk.contents)
                for match in found_strings:
                    # Filter out any explicitly "allowed" match signatures
                    if not self.signature_is_excluded(match, chunk.file_path):
                        issue = Issue(types.IssueType.RegEx, match, chunk)
                        issue.issue_detail = key
                        yield issue

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

    _repo: pygit2.Repository
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
        self, diff: pygit2.Diff
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
        for patch in diff:
            delta: pygit2.DiffDelta = patch.delta
            file_path = (
                delta.new_file.path if delta.new_file.path else delta.old_file.path
            )
            if delta.is_binary:
                self.logger.debug("Binary file skipped: %s", file_path)
                continue
            if delta.status == pygit2.GIT_DELTA_DELETED:
                self.logger.debug("Skipping as the file is deleted")
                continue
            printable_diff: str = patch.text
            if not self.global_options.scan_filenames:
                # The `printable_diff` contains diff header,
                # so we need to strip that before analyzing it
                header_length = GitScanner.header_length(printable_diff)
                printable_diff = printable_diff[header_length:]
            if self.should_scan(file_path):
                yield printable_diff, file_path

    @staticmethod
    def header_length(diff: str) -> int:
        """Compute the length of the git diff header text"""
        try:
            # Header ends after newline following line starting with "+++"
            b_file_pos = diff.index("\n+++")
            return diff.index("\n", b_file_pos + 4) + 1
        except ValueError:
            # Diff is pure header as it is a pure rename(similarity index 100%)
            return len(diff)

    def filter_submodules(self, repo: pygit2.Repository) -> None:
        """Exclude all git submodules and their contents from being scanned."""
        patterns: List[Pattern] = []
        self.logger.info("Excluding submodules paths from scan.")
        try:
            for module in repo.listall_submodules():
                patterns.append(re.compile(f"^{module.path}"))
        except AttributeError as exc:
            raise TartufoException(
                "There was an error while parsing submodules for this repository. "
                "A likely cause is that a file tree was committed in place of a "
                "submodule."
            ) from exc
        self._excluded_paths = list(set(self.excluded_paths + patterns))

    @abc.abstractmethod
    def load_repo(self, repo_path: str) -> pygit2.Repository:
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

    def load_repo(self, repo_path: str) -> pygit2.Repository:
        config_file: Optional[pathlib.Path] = None
        data: MutableMapping[str, Any] = {}
        try:
            (config_file, data) = config.load_config_from_path(
                pathlib.Path(repo_path), traverse=False
            )
        except (FileNotFoundError, types.ConfigException):
            config_file = None
        if config_file and config_file != self.global_options.config:
            signatures = data.get("exclude_signatures", None)
            if signatures:
                self.global_options.exclude_signatures = tuple(
                    set(self.global_options.exclude_signatures + tuple(signatures))
                )

            include_patterns = list(data.get("include_path_patterns", ()))
            repo_include_file = data.get("include_paths", None)
            if repo_include_file:
                repo_include_file = pathlib.Path(repo_path, repo_include_file)
                if repo_include_file.exists():
                    with repo_include_file.open() as handle:
                        include_patterns += handle.readlines()
            if include_patterns:
                include_patterns = config.compile_path_rules(include_patterns)
                self._included_paths = list(set(self.included_paths + include_patterns))

            exclude_patterns = list(data.get("exclude_path_patterns", ()))
            repo_exclude_file = data.get("exclude_paths", None)
            if repo_exclude_file:
                repo_exclude_file = pathlib.Path(repo_path, repo_exclude_file)
                if repo_exclude_file.exists():
                    with repo_exclude_file.open() as handle:
                        exclude_patterns += handle.readlines()
            if exclude_patterns:
                exclude_patterns = config.compile_path_rules(exclude_patterns)
                self._excluded_paths = list(set(self.excluded_paths + exclude_patterns))
        try:
            repo = pygit2.Repository(repo_path)
            if not self.git_options.include_submodules:
                self.filter_submodules(repo)
            return repo
        except git.GitError as exc:
            raise types.GitLocalException(str(exc)) from exc

    @property
    def chunks(self) -> Generator[types.Chunk, None, None]:
        """Yield individual diffs from the repository's history.

        :rtype: Generator[Chunk, None, None]
        :raises types.GitRemoteException: If there was an error fetching branches
        """
        already_searched: Set[bytes] = set()

        try:
            if self.git_options.branch:
                # Single branch only
                unfiltered_branches = list(self._repo.branches)
                branches = [
                    x for x in unfiltered_branches if x == self.git_options.branch
                ]

                if len(branches) == 0:
                    raise BranchNotFoundException(
                        f"Branch {self.git_options.branch} was not found."
                    )
            else:
                # Everything
                branches = list(self._repo.branches)
        except pygit2.GitError as exc:
            raise types.GitRemoteException(str(exc)) from exc

        self.logger.debug(
            "Branches to be scanned: %s",
            ", ".join([str(branch) for branch in branches]),
        )

        for branch_name in branches:
            self.logger.info("Scanning branch: %s", branch_name)
            branch: pygit2.Branch = self._repo.branches.get(branch_name)
            diff_hash: bytes
            curr_commit: pygit2.Commit = None
            prev_commit: pygit2.Commit = None
            for curr_commit in self._repo.walk(
                branch.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
            ):
                # If a commit doesn't have a parent skip diff generation since it is the first commit
                if not curr_commit.parents:
                    self.logger.debug(
                        "Skipping commit %s because it has no parents", curr_commit.hex
                    )
                    continue
                prev_commit = curr_commit.parents[0]
                diff: pygit2.Diff = self._repo.diff(prev_commit, curr_commit)
                diff_hash = hashlib.md5(
                    (str(prev_commit) + str(curr_commit)).encode("utf-8")
                ).digest()
                if diff_hash in already_searched:
                    continue
                already_searched.add(diff_hash)
                diff.find_similar()
                for blob, file_path in self._iter_diff_index(diff):
                    yield types.Chunk(
                        blob,
                        file_path,
                        util.extract_commit_metadata(curr_commit, branch),
                    )

            # Finally, yield the first commit to the branch
            if curr_commit:
                tree: pygit2.Tree = self._repo.revparse_single(curr_commit.hex).tree
                tree_diff: pygit2.Diff = tree.diff_to_tree(swap=True)
                iter_diff = self._iter_diff_index(tree_diff)
                for blob, file_path in iter_diff:
                    yield types.Chunk(
                        blob,
                        file_path,
                        util.extract_commit_metadata(curr_commit, branch),
                    )


class GitPreCommitScanner(GitScanner):
    """For use in a git pre-commit hook."""

    def __init__(
        self,
        global_options: types.GlobalOptions,
        repo_path: str,
        include_submodules: bool,
    ) -> None:
        self._include_submodules = include_submodules
        super().__init__(global_options, repo_path)

    def load_repo(self, repo_path: str) -> pygit2.Repository:
        repo = pygit2.Repository(repo_path)
        if not self._include_submodules:
            self.filter_submodules(repo)
        return repo

    @property
    def chunks(self):
        """Yield the individual file changes currently staged for commit.

        :rtype: Generator[Chunk, None, None]
        """
        diff_index = self._repo.diff("HEAD")
        for blob, file_path in self._iter_diff_index(diff_index):
            yield types.Chunk(blob, file_path, {})


class FolderScanner(ScannerBase):
    """Used to scan a folder."""

    target: str

    def __init__(
        self,
        global_options: types.GlobalOptions,
        target: str,
    ) -> None:
        """Used for scanning a folder.

        :param global_options: The options provided to the top-level tartufo command
        :param target: The local filesystem path to scan
        """
        self.target = target
        super().__init__(global_options)

    @property
    def chunks(self) -> Generator[types.Chunk, None, None]:
        """Yield the individual files in the target directory.

        :rtype: Generator[Chunk, None, None]
        """

        for blob, file_path in self._iter_folder():
            yield types.Chunk(blob, file_path, {})

    def _iter_folder(self) -> Generator[Tuple[str, str], None, None]:
        folder_path = pathlib.Path(self.target)
        for file_path in folder_path.rglob("**/*"):
            relative_path = file_path.relative_to(folder_path)
            if file_path.is_file() and self.should_scan(str(relative_path)):
                try:
                    with file_path.open("rb") as fhd:
                        data = fhd.read()
                except OSError as exc:
                    raise click.FileError(filename=str(file_path), hint=str(exc))

                try:
                    blob = data.decode("utf-8")
                    if self.global_options.scan_filenames:
                        blob = str(relative_path) + "\n" + blob
                except UnicodeDecodeError:
                    # binary file, continue
                    continue

                yield blob, str(relative_path)
