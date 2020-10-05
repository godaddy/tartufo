import copy
import json
import pathlib
import re
import shutil
from typing import (
    Any,
    Dict,
    IO,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Pattern,
    TextIO,
    Tuple,
    Union,
)

import click
import toml
import truffleHogRegexes.regexChecks

from tartufo import types, util


OptionTypes = Union[str, int, bool, None, TextIO, Tuple[TextIO, ...]]

DEFAULT_REGEXES = truffleHogRegexes.regexChecks.regexes


def load_config_from_path(
    config_path: pathlib.Path, filename: Optional[str] = None, traverse: bool = True
) -> Tuple[pathlib.Path, MutableMapping[str, Any]]:
    """Scan a path for a configuration file, and return its contents.

    All key names are normalized to remove leading "-"/"--" and replace "-"
    with "_". For example, "--repo-path" becomes "repo_path".

    In addition to checking the specified path, if ``traverse`` is ``True``,
    this will traverse up through the directory structure, looking for a
    configuration file in parent directories. For example, given this directory
    structure:

    ::

      working_dir/
      |- tartufo.toml
      |- group1/
      |  |- project1/
      |  |  |- tartufo.toml
      |  |- project2/
      |- group2/
         |- tartufo.toml
         |- project1/
         |- project2/
            |- tartufo.toml

    The following ``config_path`` values will load the configuration files at
    the corresponding paths:

    ============================ ====
    config_path                  file
    ---------------------------- ----
    working_dir/group1/project1/ working_dir/group1/project1/tartufo.toml
    working_dir/group1/project2/ working_dir/tartufo.toml
    working_dir/group2/project1/ working_dir/group2/tartufo.toml
    working_dir/group2/project2/ working_dir/group2/project2/tartufo.toml
    ============================ ====

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
                toml_file = toml.load(full_path)
                config = toml_file.get("tool", {}).get("tartufo", {})
                break
            except (toml.TomlDecodeError, OSError) as exc:
                raise types.ConfigException(f"Error reading configuration file: {exc}")
    if not config and traverse and config_path.parent != config_path:
        return load_config_from_path(config_path.parent, filename, traverse)
    if not config:
        raise FileNotFoundError(f"Could not find config file in {config_path}.")
    return (full_path, {k.replace("--", "").replace("-", "_"): v for k, v in config.items()})  # type: ignore


def read_pyproject_toml(
    ctx: click.Context, _param: click.Parameter, value: str
) -> Optional[str]:
    """Read config values from a file and load them as defaults.

    :param ctx: A context from a currently executing Click command
    :param _param: The command parameter that triggered this callback
    :param value: The value passed to the command parameter
    :raises click.FileError: If there was a problem loading the configuration
    """
    config_path: Optional[pathlib.Path] = None
    # These are the names of the arguments the sub-commands can receive.
    # NOTE: If a new sub-command is added, make sure its argument is
    #   captured in this list.
    target_args = ["repo_path", "git_url"]
    for arg in target_args:
        target_path = ctx.params.get(arg, None)
        if target_path:
            config_path = pathlib.Path(target_path)
            break
    if not config_path:
        # If no path was specified, default to the current working directory
        config_path = pathlib.Path().cwd()
    try:
        config_file, config = load_config_from_path(config_path, value)
    except FileNotFoundError as exc:
        # If a config file was specified but not found, raise an error.
        # Otherwise, pass quietly.
        if value:
            raise click.FileError(filename=str(config_path / value), hint=str(exc))
        return None
    except types.ConfigException as exc:
        # If a config file was found, but could not be read, raise an error.
        if value:
            target_file = config_path / value
        else:
            target_file = config_path / "tartufo.toml"
        raise click.FileError(filename=str(target_file), hint=str(exc))

    if not config:
        return None
    if ctx.default_map is None:
        ctx.default_map = {}
    ctx.default_map.update(config)  # type: ignore
    return str(config_file)


def configure_regexes(
    include_default: bool = True,
    rules_files: Optional[Iterable[TextIO]] = None,
    rules_repo: Optional[str] = None,
    rules_repo_files: Optional[Iterable[str]] = None,
) -> Dict[str, Pattern]:
    """Build a set of regular expressions to be used during a regex scan.

    :param include_default: Whether to include the built-in set of regexes
    :param rules_files: A list of files to load rules from
    :param rules_repo: A separate git repository to load rules from
    :param rules_repo_files: A set of patterns used to find files in the rules repo
    """
    if include_default:
        rules = copy.copy(DEFAULT_REGEXES)
    else:
        rules = {}

    if rules_files:
        all_files: List[IO[Any]] = list(rules_files)
    else:
        all_files = []
    try:
        cloned_repo = False
        repo_path = None
        if rules_repo:
            repo_path = pathlib.Path(rules_repo)
            if not repo_path.is_dir():
                repo_path = pathlib.Path(util.clone_git_repo(rules_repo))
            if not rules_repo_files:
                rules_repo_files = ("*.json",)
            for repo_file in rules_repo_files:
                all_files.extend([path.open("r") for path in repo_path.glob(repo_file)])
        if rules_files:
            for rules_file in rules_files:
                loaded = load_rules_from_file(rules_file)
                dupes = set(loaded.keys()).intersection(rules.keys())
                if dupes:
                    raise ValueError(
                        "Rule(s) were defined multiple times: {}".format(dupes)
                    )
                rules.update(loaded)
    finally:
        if cloned_repo:
            shutil.rmtree(repo_path)  # type: ignore

    return rules


def load_rules_from_file(rules_file: TextIO) -> Dict[str, Pattern]:
    """Load a set of JSON rules from a file and return them as compiled patterns.

    :param rules_file: An open file handle containing a JSON dictionary of regexes
    :raises ValueError: If the rules contain invalid JSON
    """
    regexes = {}
    try:
        new_rules = json.load(rules_file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Error loading rules from file: {}".format(rules_file.name)
        ) from exc
    for rule in new_rules:
        regexes[rule] = re.compile(new_rules[rule])
    return regexes


def compile_path_rules(patterns: Iterable[str]) -> List[Pattern]:
    """Take a list of regex strings and compile them into patterns.

    Any line starting with `#` will be ignored.

    :param patterns: The list of patterns to be compiled
    """
    return [
        re.compile(pattern.strip())
        for pattern in patterns
        if pattern and not pattern.startswith("#")
    ]
