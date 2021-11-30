# pylint: disable=too-many-instance-attributes
import enum
from dataclasses import dataclass
from typing import Any, Dict, Optional, TextIO, Tuple, Pattern


class IssueType(enum.Enum):
    """The method by which an issue was detected"""

    Entropy = "High Entropy"  # pylint: disable=invalid-name
    RegEx = "Regular Expression Match"  # pylint: disable=invalid-name


class MatchType(enum.Enum):
    """What regex method to use when looking for a match"""

    Match = "match"  # pylint: disable=invalid-name
    Search = "search"  # pylint: disable=invalid-name


class Scope(enum.Enum):
    """The scope to search for a regex match"""

    Word = "word"  # pylint: disable=invalid-name
    Line = "line"  # pylint: disable=invalid-name


class LogLevel(enum.IntEnum):
    """The various Python :py:mod:`logging` levels"""

    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3


class OutputFormat(enum.Enum):
    """The formats in which tartufo is able to output issue summaries"""

    Text = "text"  # pylint: disable=invalid-name
    Json = "json"  # pylint: disable=invalid-name
    Compact = "compact"  # pylint: disable=invalid-name


@dataclass
class GlobalOptions:
    """Configuration options for controlling scans and output

    :param rules: External files containing lists of regex patterns to match
      against
    :param rule_patterns: Dictionaries containing regex patterns to match
      against
    :param default_regexes: Whether to include built-in regex patterns in the
      scan
    :param entropy: Whether to enable entropy scans
    :param regex: Whether to enable regular expression scans
    :param scan_filenames: Whether to check filenames for potential secrets
    :param include_path_patterns: An exclusive list of paths to be scanned
    :param exclude_path_patterns: A list of paths to be excluded from the scan
    :param exclude_entropy_patterns: Patterns to be excluded from entropy
      matches
    :param exclude_signatures: Signatures of previously found findings to be
      excluded from the list of current findings
    :param exclude_findings: Signatures of previously found findings to be
      excluded from the list of current findings
    :param output_dir: A directory where detailed findings results will be
      written
    :param git_rules_repo: A remote git repository where additional rules can be
      found
    :param git_rules_files: The files in the remote rules repository to load the
      rules from
    :param config: A configuration file from which default values are pulled
    :param verbose: How verbose the scanner should be with its logging
    :param quiet: Whether to suppress all output
    :param log_timestamps: Whether to include timestamps in log output
    :param output_format: What format should be output from the scan
    :param b64_entropy_score: A number from 0.0 - 6.0 representing the
      sensitivity of b64 entropy scans
    :param hex_entropy_score: A number from 0.0 - 4.0 representing the
      sensitivity of hex entropy scans
    :param entropy_sensitivity: A number from 0 - 100 representing the
      sensitivity of entropy scans. A value of 0 will detect totally non-random
      values, while a value of 100 will detect only wholly random values.
    """

    __slots__ = (
        "rules",
        "rule_patterns",
        "default_regexes",
        "entropy",
        "regex",
        "scan_filenames",
        "include_path_patterns",
        "exclude_path_patterns",
        "exclude_entropy_patterns",
        "exclude_signatures",
        "output_dir",
        "git_rules_repo",
        "git_rules_files",
        "config",
        "verbose",
        "quiet",
        "log_timestamps",
        "output_format",
        "b64_entropy_score",
        "hex_entropy_score",
        "entropy_sensitivity",
    )
    rules: Tuple[TextIO, ...]
    rule_patterns: Tuple[Dict[str, str], ...]
    default_regexes: bool
    entropy: bool
    regex: bool
    scan_filenames: bool
    include_path_patterns: Union[Tuple[str, ...], Tuple[Dict[str, str], ...]]
    exclude_path_patterns: Union[Tuple[str, ...], Tuple[Dict[str, str], ...]]
    exclude_entropy_patterns: Tuple[Dict[str, str], ...]
    exclude_signatures: Union[Tuple[Dict[str, str], ...], Tuple[str, ...]]
    output_dir: Optional[str]
    git_rules_repo: Optional[str]
    git_rules_files: Tuple[str, ...]
    config: Optional[TextIO]
    verbose: int
    quiet: bool
    log_timestamps: bool
    output_format: Optional[OutputFormat]
    b64_entropy_score: float
    hex_entropy_score: float
    entropy_sensitivity: int


@dataclass
class GitOptions:
    """Configuration options specific to git-based scans

    :param since_commit:
    :param max_depth:
    :param branch:
    :param include_submodules:
    """

    __slots__ = ("since_commit", "max_depth", "branch", "include_submodules")
    since_commit: Optional[str]
    max_depth: int
    branch: Optional[str]
    include_submodules: bool


@dataclass
class Chunk:
    """A single "chunk" of text to be inspected during a scan

    :param contents:
    :param file_path:
    :param metadata:
    """

    __slots__ = ("contents", "file_path", "metadata")
    contents: str
    file_path: str
    metadata: Dict[str, Any]


@dataclass
class Rule:
    """A regular expression rule to be used for inspecting text during a scan

    :param name:
    :param pattern:
    :param path_pattern:
    :param re_match_type:
    :param re_match_scope:
    """

    __slots__ = ("name", "pattern", "path_pattern", "re_match_type", "re_match_scope")
    name: Optional[str]
    pattern: Pattern
    path_pattern: Optional[Pattern]
    re_match_type: MatchType
    re_match_scope: Optional[Scope]

    def __hash__(self) -> int:
        if self.path_pattern:
            return hash(f"{self.pattern.pattern}::{self.path_pattern.pattern}")
        return hash(self.pattern.pattern)


class TartufoException(Exception):
    """Base class for all package exceptions"""


class ConfigException(TartufoException):
    """Raised if there is a problem with the configuration"""


class ScanException(TartufoException):
    """Raised if there is a problem encountered during a scan"""


class BranchNotFoundException(TartufoException):
    """Raised if a branch was not found"""


class GitException(TartufoException):
    """Raised if there is a problem interacting with git"""


class GitLocalException(GitException):
    """Raised if there is an error interacting with a local git repository"""


class GitRemoteException(GitException):
    """Raised if there is an error interacting with a remote git repository"""
