# pylint: disable=too-many-instance-attributes
import enum
from dataclasses import dataclass
from typing import Any, Dict, Optional, TextIO, Tuple, Pattern


@dataclass
class GlobalOptions:
    __slots__ = (
        "json",
        "rules",
        "default_regexes",
        "entropy",
        "regex",
        "include_paths",
        "include_path_patterns",
        "exclude_paths",
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
        "compact",
    )
    json: bool
    rules: Tuple[TextIO, ...]
    default_regexes: bool
    entropy: bool
    regex: bool
    include_paths: Optional[TextIO]
    include_path_patterns: Tuple[str, ...]
    exclude_paths: Optional[TextIO]
    exclude_path_patterns: Tuple[str, ...]
    exclude_entropy_patterns: Tuple[str, ...]
    exclude_signatures: Tuple[str, ...]
    output_dir: Optional[str]
    git_rules_repo: Optional[str]
    git_rules_files: Tuple[str, ...]
    config: Optional[TextIO]
    verbose: int
    quiet: bool
    log_timestamps: bool
    compact: bool


@dataclass
class GitOptions:
    __slots__ = ("since_commit", "max_depth", "branch", "fetch", "include_submodules")
    since_commit: Optional[str]
    max_depth: int
    branch: Optional[str]
    fetch: bool
    include_submodules: bool


class IssueType(enum.Enum):
    Entropy = "High Entropy"  # pylint: disable=invalid-name
    RegEx = "Regular Expression Match"  # pylint: disable=invalid-name


@dataclass
class Chunk:
    __slots__ = ("contents", "file_path", "metadata")
    contents: str
    file_path: str
    metadata: Dict[str, Any]


@dataclass
class Rule:
    __slots__ = ("name", "pattern", "path_pattern")
    name: Optional[str]
    pattern: Pattern
    path_pattern: Optional[Pattern]

    def __hash__(self) -> int:
        if self.path_pattern:
            return hash(f"{self.pattern.pattern}::{self.path_pattern.pattern}")
        return hash(self.pattern.pattern)


class LogLevel(enum.IntEnum):
    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3


class TartufoException(Exception):
    """Base class for all package exceptions"""


class ConfigException(TartufoException):
    """Raised if there is a problem with the configuration"""


class ScanException(TartufoException):
    """Raised if there is a problem encountered during a scan"""


class GitException(TartufoException):
    """Raised if there is a problem interacting with git"""


class GitLocalException(GitException):
    """Raised if there is an error interacting with a local git repository"""


class GitRemoteException(GitException):
    """Raised if there is an error interacting with a remote git repository"""
