# pylint: disable=too-many-instance-attributes
import enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TextIO, Tuple


@dataclass
class GlobalOptions:
    json: bool
    rules: Tuple[TextIO, ...]
    default_regexes: bool
    entropy: bool
    regex: bool
    include_paths: Optional[TextIO]
    exclude_paths: Optional[TextIO]
    exclude_signatures: Tuple[str, ...]
    output_dir: Optional[str]
    git_rules_repo: Optional[str]
    git_rules_files: Tuple[str, ...]
    config: Optional[TextIO]


@dataclass
class GitOptions:
    since_commit: Optional[str]
    max_depth: int
    branch: Optional[str]


class IssueType(enum.Enum):
    Entropy = "High Entropy"
    RegEx = "Regular Expression Match"


@dataclass
class Chunk:
    contents: str
    file_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class TartufoScanException(Exception):
    pass
