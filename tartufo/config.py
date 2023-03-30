import json
import pathlib
import re
import shutil
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Pattern,
    Set,
    TextIO,
    Tuple,
    Union,
)

import click
import tomlkit

from tartufo import types, util
from tartufo.types import ConfigException, Rule, MatchType, Scope

OptionTypes = Union[str, int, bool, None, TextIO, Tuple[TextIO, ...]]

DEFAULT_PATTERN_FILE = pathlib.Path(__file__).parent / "data" / "default_regexes.json"
EMPTY_PATTERN = re.compile("")

# We need a stash of consumed configuration files
REFERENCED_CONFIG_FILES: Set[pathlib.Path] = set()


def load_config_from_path(
    config_path: pathlib.Path, filename: Optional[str] = None
) -> Tuple[pathlib.Path, MutableMapping[str, Any]]:
    """Scan a path for a configuration file, and return its contents.

    All key names are normalized to remove leading "-"/"--" and replace "-"
    with "_". For example, "--repo-path" becomes "repo_path".

    :param config_path: The path to search for configuration files
    :param filename: A specific filename to look for. By default, this will look
      for both ``tartufo.toml`` and then ``pyproject.toml``.
    :raises FileNotFoundError: If no config file was found
    :raises types.ConfigException: If a config file was found, but could not be
      read
    :returns: A tuple consisting of the config file that was discovered, and the
      contents of that file loaded in as TOML data
    """
    config: MutableMapping[str, Any] = {}
    full_path: Optional[pathlib.Path] = None
    if filename:
        config_filenames = [filename]
    else:
        config_filenames = ["tartufo.toml", "pyproject.toml"]
    for possibility in config_filenames:
        full_path = config_path / possibility
        if full_path.exists():
            try:
                with open(full_path, encoding="utf8") as file:
                    toml_file = tomlkit.loads(file.read())
                    config = toml_file.get("tool", {}).get("tartufo", {})  # type: ignore
                break
            except (tomlkit.exceptions.ParseError, OSError) as exc:
                raise types.ConfigException(f"Error reading configuration file: {exc}")
    if not config:
        raise FileNotFoundError(f"Could not find config file in {config_path}.")
    return (full_path, {k.replace("--", "").replace("-", "_"): v for k, v in config.items()})  # type: ignore


def read_pyproject_toml(
    ctx: click.Context, _param: click.Parameter, value: Tuple[str, ...]
) -> None:
    """Read config values from one or more files and load them as defaults.

    :param ctx: A context from a currently executing Click command
    :param _param: The command parameter that triggered this callback
    :param value: The value(s) passed to the command parameter
    :raises click.FileError: If there was a problem loading the configuration

    This handles loading and merging all files specified on the tartufo command
    line using `--config`. A set of fully-resolved Path objects for all ingested
    configuration files is saved in config.REFERENCED_CONFIG_FILES.
    """

    global REFERENCED_CONFIG_FILES  # pylint: disable=[global-variable-not-assigned]

    config_path = pathlib.Path().cwd()
    consolidated_config: Dict[str, Any] = {}
    for config_candidate in value:
        try:
            config_file, config_data = load_config_from_path(
                config_path, config_candidate
            )
        except FileNotFoundError as exc:
            raise click.FileError(
                filename=str(config_path / config_candidate), hint=str(exc)
            )
        except types.ConfigException as exc:
            # If a config file was found, but could not be read, raise an error.
            target_file = config_path / config_candidate
            raise click.FileError(filename=str(target_file), hint=str(exc))

        # Ignore empty files
        if not config_data:
            continue

        # A simple .update() does not merge list-valued members
        for key, val in config_data.items():
            if key in consolidated_config and isinstance(val, list):
                # Concatenate list-valued members
                consolidated_config[key].extend(val)
            else:
                # Create (or overwrite) everything else
                consolidated_config[key] = val  # type: ignore [index]

        REFERENCED_CONFIG_FILES.add(config_file.resolve())

    # Store accumulated data in ctx.default_map. Completely replacing the entire
    # thing (which appears to be a Mapping[str, Any]) seems to be a little sketchy
    # but we've been doing that for a while and empirically it works.
    ctx.default_map = consolidated_config


def configure_regexes(
    include_default: bool = True,
    rule_patterns: Optional[Iterable[Dict[str, str]]] = None,
    rules_repo: Optional[str] = None,
    rules_repo_files: Optional[Iterable[str]] = None,
) -> Set[Rule]:
    """Build a set of regular expressions to be used during a regex scan.

    :param include_default: Whether to include the built-in set of regexes
    :param rules_files: A list of files to load rules from
    :param rule_patterns: A set of previously-collected rules
    :param rules_repo: A separate git repository to load rules from
    :param rules_repo_files: A set of patterns used to find files in the rules repo
    :returns: Set of `Rule` objects to be used for regex scans
    """

    if include_default:
        with DEFAULT_PATTERN_FILE.open() as handle:
            rules = load_rules_from_file(handle)
    else:
        rules = set()

    if rule_patterns:
        try:
            for pattern in rule_patterns:
                rule = Rule(
                    name=pattern["reason"],
                    pattern=re.compile(pattern["pattern"]),
                    path_pattern=re.compile(pattern.get("path-pattern", "")),
                    re_match_type=MatchType.Search,
                    re_match_scope=None,
                )
                rules.add(rule)
        except KeyError as exc:
            raise ConfigException(
                f"Invalid rule-pattern; both reason and pattern are required fields. Rule: {pattern}"
            ) from exc

    all_files = []
    try:
        cloned_repo = False
        repo_path = None
        if rules_repo:
            repo_path = pathlib.Path(rules_repo)
            try:
                if not repo_path.is_dir():
                    cloned_repo = True
            except OSError:  # pragma: no cover
                # If a git URL is passed in, Windows will raise an OSError on `is_dir()`
                cloned_repo = True
            finally:
                if cloned_repo:
                    repo_path, _ = util.clone_git_repo(rules_repo)
            if not rules_repo_files:
                rules_repo_files = ("*.json",)
            for repo_file in rules_repo_files:
                all_files.extend([path.open("r") for path in repo_path.glob(repo_file)])
        if all_files:
            for rules_file in all_files:
                rules.update(load_rules_from_file(rules_file))
    finally:
        if cloned_repo:
            shutil.rmtree(repo_path, onerror=util.del_rw)  # type: ignore

    return rules


def load_rules_from_file(rules_file: TextIO) -> Set[Rule]:
    """Load a set of JSON rules from a file and return them as compiled patterns.

    :param rules_file: An open file handle containing a JSON dictionary of regexes
    :raises ValueError: If the rules contain invalid JSON
    """

    rules: Set[Rule] = set()
    try:
        new_rules = json.load(rules_file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Error loading rules from file: {rules_file.name}") from exc
    for rule_name, rule_definition in new_rules.items():
        try:
            path_pattern = rule_definition.get("path_pattern", None)
            rule = Rule(
                name=rule_name,
                pattern=re.compile(rule_definition["pattern"]),
                path_pattern=re.compile(path_pattern)
                if path_pattern
                else EMPTY_PATTERN,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        except AttributeError:
            rule = Rule(
                name=rule_name,
                pattern=re.compile(rule_definition),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        rules.add(rule)
    return rules


def compile_path_rules(patterns: Iterable[str]) -> List[Pattern]:
    """Take a list of regex strings and compile them into patterns.

    Any line starting with `#` will be ignored.

    :param patterns: The list of patterns to be compiled
    """
    stripped = (p.strip() for p in patterns)
    return [
        re.compile(pattern)
        for pattern in stripped
        if pattern and not pattern.startswith("#")
    ]


def compile_rules(patterns: Iterable[Dict[str, str]], exclude_type: str) -> List[Rule]:
    """Take a list of regex string with paths and compile them into a List of Rule.

    :param patterns: The list of patterns to be compiled
    :return: List of Rule objects
    """
    rules: List[Rule] = []
    for pattern in patterns:
        try:
            match_type = MatchType(pattern.get("match-type", MatchType.Search.value))
        except ValueError as exc:
            raise ConfigException(
                f"Invalid value for match-type: {pattern.get('match-type')}"
            ) from exc
        if exclude_type == "regex":
            # regex exclusions always have line scope
            scope = Scope.Line
        else:
            # entropy exclusions can specify scope
            try:
                scope = Scope(pattern.get("scope", Scope.Line.value))
            except ValueError as exc:
                raise ConfigException(
                    f"Invalid value for scope: {pattern.get('scope')}"
                ) from exc
        try:
            rules.append(
                Rule(
                    name=pattern.get("reason", None),  # type: ignore[union-attr]
                    pattern=re.compile(pattern["pattern"]),  # type: ignore[index]
                    path_pattern=re.compile(pattern.get("path-pattern", "")),  # type: ignore[union-attr]
                    re_match_type=match_type,
                    re_match_scope=scope,
                )
            )
        except KeyError as exc:
            raise ConfigException(
                f"Invalid exclude-{exclude_type}-patterns: {patterns}"
            ) from exc
    return rules
