import copy
import json
import re
import shutil
from functools import partial
from typing import (
    Any,
    Dict,
    IO,
    Iterable,
    List,
    Optional,
    Pattern,
    TextIO,
    Tuple,
    Union,
)

import click
import toml
import truffleHogRegexes.regexChecks
from tartufo import util

try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib  # type: ignore


err = partial(  # pylint: disable=invalid-name
    click.secho, fg="red", bold=True, err=True
)
OptionTypes = Union[str, int, bool, None, TextIO, Tuple[TextIO, ...]]
OptionsDict = Dict[str, OptionTypes]
PatternDict = Dict[str, Union[str, Pattern]]

DEFAULT_REGEXES = truffleHogRegexes.regexChecks.regexes


def read_pyproject_toml(ctx, _param, value):
    # type: (click.Context, click.Parameter, str) -> Optional[str]
    if not value:
        root_path = ctx.params.get("repo_path", None)
        if not root_path:
            root_path = "."
        root_path = pathlib.Path(root_path).resolve()
        config_path = root_path / "pyproject.toml"
        if config_path.is_file():
            value = str(config_path)
        else:
            config_path = root_path / "tartufo.toml"
            if config_path.is_file():
                value = str(config_path)
            else:
                return None
    try:
        toml_file = toml.load(value)
        config = toml_file.get("tool", {}).get("tartufo", {})
    except (toml.TomlDecodeError, OSError) as exc:
        raise click.FileError(
            filename=str(config_path),
            hint="Error reading configuration file: {}".format(exc),
        )
    if not config:
        return None
    if ctx.default_map is None:
        ctx.default_map = {}
    ctx.default_map.update(  # type: ignore
        {k.replace("--", "").replace("-", "_"): v for k, v in config.items()}
    )
    return str(value)


def configure_regexes(
    include_default=True,  # type: bool
    rules_files=None,  # type: Optional[Iterable[TextIO]]
    rules_repo=None,  # type: Optional[str]
    rules_repo_files=None,  # type: Optional[Iterable[str]]
):
    # type: (...) -> PatternDict
    if include_default:
        rules = copy.copy(DEFAULT_REGEXES)
    else:
        rules = {}

    if rules_files:
        all_files = list(rules_files)  # type: List[IO[Any]]
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


def load_rules_from_file(rules_file):
    # type: (TextIO) -> Dict[str, Pattern]
    regexes = {}
    try:
        new_rules = json.load(rules_file)
    except json.JSONDecodeError:
        raise ValueError("Error loading rules from file: {}".format(rules_file.name))
    for rule in new_rules:
        regexes[rule] = re.compile(new_rules[rule])
    return regexes


def compile_path_rules(patterns):
    # type: (Iterable[str]) -> List[Pattern]
    return [
        re.compile(pattern.strip())
        for pattern in patterns
        if pattern and not pattern.startswith("#")
    ]
