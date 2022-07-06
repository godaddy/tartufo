# -*- coding: utf-8 -*-

import abc
from collections import Counter
from functools import lru_cache
import hashlib
import logging
import math
import pathlib
import re
import threading
import tempfile
import pickle
import gzip
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
    IO,
)
import warnings

from cached_property import cached_property
import click
import git
import pygit2

from tartufo import config, types, util
from tartufo.types import (
    BranchNotFoundException,
    Rule,
    TartufoException,
    MatchType,
    Scope,
)

BASE64_REGEX = re.compile(r"[A-Z0-9=+/_-]+", re.IGNORECASE)
HEX_REGEX = re.compile(r"[0-9A-F]+", re.IGNORECASE)


class Issue:
    """Represent an issue found while scanning a target."""

    __slots__ = (
        "chunk",
        "issue_type",
        "issue_detail",
        "matched_string",
    )

    chunk: types.Chunk
    issue_type: types.IssueType
    issue_detail: Optional[str]
    matched_string: str
    OUTPUT_SEPARATOR: str = "~~~~~~~~~~~~~~~~~~~~~"

    def __init__(
        self, issue_type: types.IssueType, matched_string: str, chunk: types.Chunk
    ) -> None:
        """
        :param issue_type: What type of scan identified this issue
        :param matched_string: The string that was identified as a potential issue
        :param chunk: The chunk of data where the match was found
        """
        self.issue_detail = None
        self.issue_type = issue_type
        self.matched_string = matched_string
        self.chunk = chunk

    def as_dict(self, compact=False) -> Dict[str, Optional[str]]:
        """Return a dictionary representation of an issue.

        This is primarily meant to aid in JSON serialization.

        :param compact: True to return a dictionary with fewer fields.
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
        """Generate a stable hash-based signature uniquely identifying this issue."""
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


# pylint: disable=too-many-public-methods
class ScannerBase(abc.ABC):  # pylint: disable=too-many-instance-attributes
    """Provide the base, generic functionality needed by all scanners.

    In fact, this contains all of the actual scanning logic. This part of the
    application should never differ; the part that differs, and the part that is
    left abstract here, is what content is provided to the various scans. For
    this reason, the `chunks` property is left abstract. It is up to the various
    scanners to implement this property, in the form of a generator, to yield
    all the individual pieces of content to be scanned.
    """

    _completed: bool = False
    _included_paths: Optional[List[Pattern]] = None
    _excluded_paths: Optional[List[Pattern]] = None
    _excluded_entropy: Optional[List[Rule]] = None
    _rules_regexes: Optional[Set[Rule]] = None
    global_options: types.GlobalOptions
    logger: logging.Logger
    _scan_lock: threading.Lock = threading.Lock()
    _excluded_signatures: Optional[Tuple[str, ...]] = None
    _config_data: MutableMapping[str, Any] = {}
    _issue_list: List[Issue] = []
    _issue_file: Optional[IO] = None
    _issue_count: int

    def __init__(self, options: types.GlobalOptions) -> None:
        """
        :param options: A set of options to control the behavior of the scanner
        """
        self.global_options = options
        self.logger = logging.getLogger(__name__)

    def compute_scaled_entropy_limit(self, maximum_bitrate: float) -> float:
        """Determine low entropy cutoff for specified bitrate

        :param maximum_bitrate: How many bits does each character represent?
        :returns: Entropy detection threshold scaled to the input bitrate
        """

        if self.global_options.entropy_sensitivity is None:
            sensitivity = 75
        else:
            sensitivity = self.global_options.entropy_sensitivity
        return float(sensitivity) / 100.0 * maximum_bitrate

    @cached_property
    def hex_entropy_limit(self) -> float:
        """Returns low entropy limit for suspicious hexadecimal encodings"""

        # For backwards compatibility, allow the caller to manipulate this score
        # # directly (but complain about it).
        if self.global_options.hex_entropy_score:
            warnings.warn(
                "--hex-entropy-score is deprecated and will be removed in tartufo 4.x. "
                "Please use --entropy-sensitivity instead.",
                DeprecationWarning,
            )
            return self.global_options.hex_entropy_score

        # Each hexadecimal digit represents a 4-bit number, so we want to scale
        # the base score by this amount to account for the efficiency of the
        # string representation we're examining.
        return self.compute_scaled_entropy_limit(4.0)

    @cached_property
    def b64_entropy_limit(self) -> float:
        """Returns low entropy limit for suspicious base64 encodings"""

        # For backwards compatibility, allow the caller to manipulate this score
        # # directly (but complain about it).
        if self.global_options.b64_entropy_score:
            warnings.warn(
                "--b64-entropy-score is deprecated and will be removed in tartufo 4.x. "
                "Please use --entropy-sensitivity instead.",
                DeprecationWarning,
            )
            return self.global_options.b64_entropy_score

        # Each 4-character base64 group represents 3 8-bit bytes, i.e. an effective
        # bit rate of 24/4 = 6 bits per character. We want to scale the base score
        # by this amount to account for the efficiency of the string representation
        # we're examining.
        return self.compute_scaled_entropy_limit(6.0)

    @property
    def issue_count(self) -> int:
        return self._issue_count

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

        return list(self.scan())

    @property
    def config_data(self) -> MutableMapping[str, Any]:
        r"""Supplemental configuration to be merged into the \*_options information."""
        return self._config_data

    @config_data.setter
    def config_data(self, data: MutableMapping[str, Any]) -> None:
        self._config_data = data

    @property
    def included_paths(self) -> List[Pattern]:
        """Get a list of regexes used as an exclusive list of paths to scan"""
        if self._included_paths is None:
            self.logger.info("Initializing included paths")
            patterns: Set[str] = set()
            deprecated = False
            for pattern in tuple(
                self.global_options.include_path_patterns or []
            ) + tuple(self.config_data.get("include_path_patterns", [])):
                if isinstance(pattern, dict):
                    try:
                        patterns.add(pattern["path-pattern"])
                    except KeyError as exc:
                        raise types.ConfigException(
                            "Required key path-pattern missing in include-path-patterns"
                        ) from exc
                elif isinstance(pattern, str):
                    deprecated = True
                    patterns.add(pattern)
                else:
                    raise types.ConfigException(
                        f"{type(pattern).__name__} pattern is illegal in include-path-patterns"
                    )
            if deprecated:
                warnings.warn(
                    "Old format of --include-path-patterns option and config file setup include-path-patterns "
                    "= ['inclusion pattern'] has been deprecated and will be removed in tartufo 4.x. "
                    "Make sure all the inclusions are set up using new pattern i.e. include-path-patterns = "
                    "[{path-pattern='inclusion pattern',reason='reason for inclusion'}] in the config file",
                    DeprecationWarning,
                )
            self._included_paths = config.compile_path_rules(patterns)
        return self._included_paths

    @property
    def excluded_entropy(self) -> List[Rule]:
        """Get a list of regexes used as an exclusive list of paths to scan."""
        if self._excluded_entropy is None:
            self.logger.info("Initializing excluded entropy patterns")
            patterns = list(self.global_options.exclude_entropy_patterns or ()) + list(
                self.config_data.get("exclude_entropy_patterns", ())
            )
            self._excluded_entropy = config.compile_rules(patterns) if patterns else []
            self.logger.debug(
                "Excluded entropy was initialized as: %s", self._excluded_entropy
            )
        return self._excluded_entropy

    @property
    def excluded_paths(self) -> List[Pattern]:
        """Get a list of regexes used to match paths to exclude from the scan"""
        if self._excluded_paths is None:
            self.logger.info("Initializing excluded paths")
            patterns: Set[str] = set()
            deprecated = False
            for pattern in tuple(
                self.global_options.exclude_path_patterns or []
            ) + tuple(self.config_data.get("exclude_path_patterns", [])):
                if isinstance(pattern, dict):
                    try:
                        patterns.add(pattern["path-pattern"])
                    except KeyError as exc:
                        raise types.ConfigException(
                            "Required key path-pattern missing in exclude-path-patterns"
                        ) from exc
                elif isinstance(pattern, str):
                    deprecated = True
                    patterns.add(pattern)
                else:
                    raise types.ConfigException(
                        f"{type(pattern).__name__} pattern is illegal in exclude-path-patterns"
                    )
            if deprecated:
                warnings.warn(
                    "Old format of --exclude-path-patterns option and config file setup exclude-path-patterns "
                    "= ['exclusion pattern'] has been deprecated and will be removed in tartufo 4.x. "
                    "Make sure all the exclusions are set up using new pattern i.e. exclude-path-patterns = "
                    "[{path-pattern='exclusion pattern',reason='reason for exclusion'}] in the config file",
                    DeprecationWarning,
                )
            self._excluded_paths = config.compile_path_rules(patterns)
        return self._excluded_paths

    @property
    def rules_regexes(self) -> Set[Rule]:
        """Get a set of regular expressions to scan the code for.

        :raises types.ConfigException: If there was a problem compiling the rules
        """
        if self._rules_regexes is None:
            self.logger.info("Initializing regex rules")
            try:
                self._rules_regexes = config.configure_regexes(
                    include_default=self.global_options.default_regexes,
                    rules_files=self.global_options.rules,
                    rule_patterns=self.global_options.rule_patterns,
                    rules_repo=self.global_options.git_rules_repo,
                    rules_repo_files=self.global_options.git_rules_files,
                )
            except (ValueError, re.error) as exc:
                self.logger.exception("Error loading regex rules", exc_info=exc)
                raise types.ConfigException(str(exc)) from exc
            self.logger.debug(
                "Regex rules were initialized as: %s", self._rules_regexes
            )
        return self._rules_regexes

    @lru_cache(maxsize=None)
    def should_scan(self, file_path: str) -> bool:
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

    @cached_property
    def excluded_signatures(self) -> Tuple[str, ...]:
        """Get a list of the signatures of findings to be excluded from the scan results.

        :returns: The signatures to be excluded from scan results
        """
        if self._excluded_signatures is None:
            signatures: Set[str] = set()
            deprecated = False
            for signature in tuple(
                self.global_options.exclude_signatures or []
            ) + tuple(self.config_data.get("exclude_signatures", [])):
                if isinstance(signature, dict):
                    try:
                        signatures.add(signature["signature"])
                    except KeyError as exc:
                        raise types.ConfigException(
                            "Required key signature missing in exclude-signatures"
                        ) from exc
                elif isinstance(signature, str):
                    deprecated = True
                    signatures.add(signature)
                else:
                    raise types.ConfigException(
                        f"{type(signature).__name__} signature is illegal in exclude-signatures"
                    )
            if deprecated:
                warnings.warn(
                    "Configuring exclude-signatures as string has been deprecated and support for this format will "
                    "be removed in tartufo 4.x. Please update your exclude-signatures configuration to "
                    "an array of tables. For example: exclude-signatures = [{signature='signature', reason='The "
                    "reason of excluding the signature'}]",
                    DeprecationWarning,
                )
            self._excluded_signatures = tuple(signatures)
        return self._excluded_signatures

    def signature_is_excluded(self, blob: str, file_path: str) -> bool:
        """Find whether the signature of some data has been excluded in configuration.

        :param blob: The piece of data which is being scanned
        :param file_path: The path and file name for the data being scanned
        """
        return (
            blob
            in self.excluded_signatures  # Signatures themselves pop up as entropy matches
            or util.generate_signature(blob, file_path) in self.excluded_signatures
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def rule_matches(rule: Rule, string: str, line: str, path: str) -> bool:
        """
        Match string and path against rule.

        :param rule: Rule to perform match
        :param string: string to match against rule pattern
        :param line: Source line containing string of interest
        :param path: path to match against rule path_pattern
        :return: True if string and path matched, False otherwise.
        """
        match = False
        if rule.re_match_scope == Scope.Word:
            scope = string
        elif rule.re_match_scope == Scope.Line:
            scope = line
        else:
            raise TartufoException(f"Invalid value for scope: {rule.re_match_scope}")
        if rule.re_match_type == MatchType.Match:
            if rule.pattern:
                match = rule.pattern.match(scope) is not None
            if rule.path_pattern:
                match = match and rule.path_pattern.match(path) is not None
        elif rule.re_match_type == MatchType.Search:
            if rule.pattern:
                match = rule.pattern.search(scope) is not None
            if rule.path_pattern:
                match = match and rule.path_pattern.search(path) is not None

        return match

    def entropy_string_is_excluded(self, string: str, line: str, path: str) -> bool:
        """Find whether the signature of some data has been excluded in configuration.

        :param string: String to check against rule pattern
        :param line: Source line containing string of interest
        :param path: Path to check against rule path pattern
        :return: True if excluded, False otherwise
        """

        return bool(self.excluded_entropy) and any(
            ScannerBase.rule_matches(p, string, line, path)
            for p in self.excluded_entropy
        )

    @lru_cache(maxsize=None)
    def calculate_entropy(self, data: str) -> float:
        """Calculate the Shannon entropy for a piece of data.

        This essentially calculates the overall probability for each character
        in `data` to be to be present. By doing this, we can tell how random a
        string appears to be.

        Adapted from http://blog.dkbza.org/2007/05/scanning-data-for-entropy-anomalies.html

        :param data: The data to be scanned for its entropy
        :return: The amount of entropy detected in the data
        """
        if not data:
            return 0.0
        frequency = Counter(data)
        entropy = 0.0
        float_size = float(len(data))
        for count in frequency.values():
            probability = float(count) / float_size
            entropy += -probability * math.log2(probability)
        return entropy

    @property
    def issue_file(self) -> IO:
        if not self._issue_file:
            self._issue_file = (
                tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
                    dir=self.global_options.temp_dir
                )
            )
        return self._issue_file

    def load_issues(self) -> Generator[Issue, None, None]:
        # Rewind the issue_file
        self.logger.debug("Rewinding pickle file")
        self.issue_file.seek(0)
        while True:
            try:
                length = int.from_bytes(self.issue_file.read(4), "little")
                buf = self.issue_file.read(length)
                yield from pickle.loads(gzip.decompress(buf))
            except EOFError:
                self.logger.debug("pickle.load raised EOFError, exiting")
                yield from self._issue_list
                return

    def store_issue(self, issue: Issue) -> None:
        self._issue_count = self._issue_count + 1
        self._issue_list.append(issue)
        if len(self._issue_list) >= self.global_options.buffer_size:
            compressed = gzip.compress(pickle.dumps(self._issue_list), compresslevel=9)
            length = len(compressed)
            self.issue_file.write(length.to_bytes(4, "little"))
            self.issue_file.write(compressed)
            self._issue_list.clear()

    def scan(
        self,
    ) -> Generator[Issue, None, None]:
        """Run the requested scans against the target data.

        This will iterate through all chunks of data as provided by the scanner
        implementation, and run all requested scans against it, as specified in
        `self.global_options`.

        The scan method is thread-safe; if multiple concurrent scans are requested,
        the first will run to completion while other callers are blocked (after
        which they will each execute in turn, yielding cached issues without
        repeating the underlying repository scan).

        :raises types.ConfigException: If there were problems with the
          scanner's configuration
        """

        # I cannot find any written description of the python memory model. The
        # correctness of this code in multithreaded environments relies on the
        # expectation that the write to _completed at the bottom of the critical
        # section cannot be reordered to appear after the implicit release of
        # _scan_lock (when viewed from a competing thread).
        self.logger.debug("Waiting for scan lock")
        with self._scan_lock:
            if self._completed:
                self.logger.debug("Scan already completed")
                yield from self.load_issues()
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
            self._issue_count = 0
            for chunk in self.chunks:  # pylint: disable=too-many-nested-blocks
                # Run regex scans first to trigger a potential fast fail for bad config
                if self.global_options.regex and self.rules_regexes:
                    for issue in self.scan_regex(chunk):
                        self.store_issue(issue)
                        yield issue
                if self.global_options.entropy:
                    for issue in self.scan_entropy(chunk):
                        self.store_issue(issue)
                        yield issue

            self._completed = True
            self.logger.info("Found %d issues.", self._issue_count)

    def scan_entropy(
        self,
        chunk: types.Chunk,
    ) -> Generator[Issue, None, None]:
        """Scan a chunk of data for apparent high entropy.

        :param chunk: The chunk of data to be scanned
        """

        for line in (x for x in chunk.contents.split("\n") if x):
            # If the chunk is diff output, the first character of each line is
            # generated metadata ("+", "-", etc.) that is not part of actual
            # repository content, and it should be ignored.
            extra_char: Optional[str]
            if chunk.is_diff:
                extra_char = line[0]
                analyze = line[1:]
            else:
                extra_char = None
                analyze = line
            for word in analyze.split():
                for string in util.find_strings_by_regex(word, BASE64_REGEX):
                    yield from self.evaluate_entropy_string(
                        chunk, analyze, string, self.b64_entropy_limit, extra_char
                    )
                for string in util.find_strings_by_regex(word, HEX_REGEX):
                    yield from self.evaluate_entropy_string(
                        chunk, analyze, string, self.hex_entropy_limit, extra_char
                    )
                extra_char = None

    def evaluate_entropy_string(
        self,
        chunk: types.Chunk,
        line: str,
        string: str,
        min_entropy_score: float,
        backwards_compatibility_prefix: Optional[str],
    ) -> Generator[Issue, None, None]:
        """Check entropy string using entropy characters and score.

        :param chunk: The chunk of data to check
        :param line: Source line containing string of interest
        :param string: String to check
        :param min_entropy_score: Minimum entropy score to flag
        :param backwards_compatibility_prefix: Possible prefix character
        :return: Generator of issues flagged

        If the string in "string" would result in an Issue (i.e. it has high
        entropy and is not excluded), and backwards_compatibility_prefix is not
        None, re-check for exclusions based on "prefix" + "string". This preserves
        the utility of signatures generated by earlier tartufo versions which did
        not handle "diff" chunks correctly.
        """

        if not self.signature_is_excluded(string, chunk.file_path):
            entropy_score = self.calculate_entropy(string)
            if entropy_score > min_entropy_score:
                if self.entropy_string_is_excluded(string, line, chunk.file_path):
                    self.logger.debug("line containing entropy was excluded: %s", line)
                elif (
                    backwards_compatibility_prefix is not None
                    and self.signature_is_excluded(
                        backwards_compatibility_prefix + string, chunk.file_path
                    )
                ):
                    self.logger.debug(
                        "line containing entropy was excluded (old signature): %s", line
                    )
                    # We should tell the user to update their old signature
                    new_signature = util.generate_signature(string, chunk.file_path)
                    old_signature = util.generate_signature(
                        backwards_compatibility_prefix + string, chunk.file_path
                    )
                    warnings.warn(
                        f"Signature {old_signature} was generated by an old version of tartufo and is deprecated. "
                        "tartufo 4.x will not recognize this signature. "
                        f"Please update your configuration to use signature {new_signature} instead.",
                        DeprecationWarning,
                    )

                else:
                    yield Issue(types.IssueType.Entropy, string, chunk)

    def scan_regex(self, chunk: types.Chunk) -> Generator[Issue, None, None]:
        """Scan a chunk of data for matches against the configured regexes.

        :param chunk: The chunk of data to be scanned
        """

        for rule in self.rules_regexes:
            if rule.path_pattern is None or rule.path_pattern.match(chunk.file_path):
                found_strings = rule.pattern.findall(chunk.contents)
                for match in found_strings:
                    # Filter out any explicitly "allowed" match signatures
                    if not self.signature_is_excluded(match, chunk.file_path):
                        issue = Issue(types.IssueType.RegEx, match, chunk)
                        issue.issue_detail = rule.name
                        yield issue

    @property
    @abc.abstractmethod
    def chunks(self) -> Generator[types.Chunk, None, None]:
        """Yield "chunks" of data to be scanned.

        Examples of "chunks" would be individual git commit diffs, or the
        contents of individual files.
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

        :param diff: The diff index / commit to be iterated over
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
        """Compute the length of the git diff header text.

        :param diff: The diff being inspected for a header
        """
        try:
            # Header ends after newline following line starting with "+++"
            b_file_pos = diff.index("\n+++")
            return diff.index("\n", b_file_pos + 4) + 1
        except ValueError:
            # Diff is pure header as it is a pure rename(similarity index 100%)
            return len(diff)

    def filter_submodules(self, repo: pygit2.Repository) -> None:
        """Exclude all git submodules and their contents from being scanned.

        :param repo: The repository being scanned
        """
        patterns: List[Pattern] = []
        self.logger.info("Excluding submodules paths from scan.")
        try:
            for module in repo.listall_submodules():
                submodule = repo.lookup_submodule(module)
                patterns.append(re.compile(f"^{submodule.path}"))
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
        if config_file and str(config_file) != self.global_options.config:
            self.config_data = data
        try:
            repo = pygit2.Repository(repo_path)
            if not repo.is_bare:
                if not self.git_options.include_submodules:
                    self.filter_submodules(repo)
            return repo
        except git.GitError as exc:
            raise types.GitLocalException(str(exc)) from exc

    @property
    def chunks(self) -> Generator[types.Chunk, None, None]:
        """Yield individual diffs from the repository's history.

        :raises types.GitRemoteException: If there was an error fetching branches
        """
        already_searched: Set[bytes] = set()

        try:
            if self.git_options.branch:
                # Single branch only
                branch = self._repo.branches.get(self.git_options.branch)
                if not branch:
                    raise BranchNotFoundException(
                        f"Branch {self.git_options.branch} was not found."
                    )
                branches = [self.git_options.branch]
            else:
                # Everything
                if util.is_shallow_clone(self._repo):
                    # If this is a shallow clone, examine the repo head as a single
                    # commit to scan all files at once
                    branches = ["HEAD"]
                else:
                    # We use `self._repo.branches` here so that we make sure to
                    # scan not only the locally checked out branches (as provided
                    # by self._repo.listall_branches()), but to also scan all
                    # available remote refs
                    branches = list(self._repo.branches)
        except pygit2.GitError as exc:
            raise types.GitRemoteException(str(exc)) from exc

        self.logger.debug(
            "Branches to be scanned: %s",
            ", ".join([str(branch) for branch in branches]),
        )

        for branch_name in branches:
            self.logger.info("Scanning branch: %s", branch_name)
            if branch_name == "HEAD":
                commits = [self._repo.get(self._repo.head.target)]
            else:
                branch = self._repo.branches.get(branch_name)
                try:
                    commits = self._repo.walk(
                        branch.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
                    )
                except AttributeError:
                    self.logger.debug(
                        "Skipping branch %s because it cannot be resolved.", branch_name
                    )
                    continue
            diff_hash: bytes
            curr_commit: pygit2.Commit = None
            prev_commit: pygit2.Commit = None
            for curr_commit in commits:
                try:
                    prev_commit = curr_commit.parents[0]
                except (IndexError, KeyError, TypeError):
                    # IndexError: current commit has no parents
                    # KeyError: current commit has parents which are not local
                    # If a commit doesn't have a parent skip diff generation since it is the first commit
                    self.logger.debug(
                        "Skipping commit %s because it has no parents", curr_commit.hex
                    )
                    continue
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
                        util.extract_commit_metadata(curr_commit, branch_name),
                        True,
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
                        util.extract_commit_metadata(curr_commit, branch_name),
                        True,
                    )


class GitPreCommitScanner(GitScanner):
    """For use in a git pre-commit hook."""

    def __init__(
        self,
        global_options: types.GlobalOptions,
        repo_path: str,
        include_submodules: bool,
    ) -> None:
        """
        :param global_options: The options provided to the top-level tartufo command
        :param repo_path: The local filesystem path pointing to the repository
        :param include_submodules: Whether to scan git submodules in the repository
        """
        self._include_submodules = include_submodules
        super().__init__(global_options, repo_path)

    def load_repo(self, repo_path: str) -> pygit2.Repository:
        repo = pygit2.Repository(repo_path)
        if not self._include_submodules:
            self.filter_submodules(repo)
        return repo

    @property
    def chunks(self):
        """Yield the individual file changes currently staged for commit."""
        # See the meaning of the flags below
        # here: https://github.com/libgit2/libgit2/blob/13502d9e7f6c51a5f93ea39e14db707d382dc996/include/git2/diff.h#L49
        # and here: https://github.com/libgit2/libgit2/blob/13502d9e7f6c51a5f93ea39e14db707d382dc996/include/git2/diff.h#L156
        #
        # These were introduced so that tartufo would scan newly added files that are staged. Without these flags, tartufo
        # will only scan files that have been committed at least once, because a file still counts as "untracked" even
        # after it has been added to the index. It only becomes tracked once it has actually been committed.
        diff_index = self._repo.diff(
            "HEAD",
            cached=True,
            flags=pygit2.GIT_DIFF_INCLUDE_UNTRACKED
            | pygit2.GIT_DIFF_SHOW_UNTRACKED_CONTENT,
        )
        for blob, file_path in self._iter_diff_index(diff_index):
            yield types.Chunk(blob, file_path, {}, True)


class FolderScanner(ScannerBase):
    """Used to scan a folder."""

    target: str
    recurse: bool

    def __init__(
        self, global_options: types.GlobalOptions, target: str, recurse: bool
    ) -> None:
        """Used for scanning a folder.

        :param global_options: The options provided to the top-level tartufo command
        :param target: The local filesystem path to scan
        :param recurse: Whether to recurse into sub-folders of the target
        """
        self.target = target
        self.recurse = recurse
        super().__init__(global_options)

    @property
    def chunks(self) -> Generator[types.Chunk, None, None]:
        """Yield the individual files in the target directory."""

        for blob, file_path in self._iter_folder():
            yield types.Chunk(blob, file_path, {}, False)

    def _iter_folder(self) -> Generator[Tuple[str, str], None, None]:
        folder_path = pathlib.Path(self.target)
        files = folder_path.rglob("**/*") if self.recurse else folder_path.glob("*")
        for file_path in files:
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
