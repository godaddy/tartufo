import json
import re
import shutil
from functools import partial
from typing import cast, Dict, List, Optional, Pattern, TextIO, Tuple, Union

import click
import toml
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


def read_pyproject_toml(ctx, _param, value):
    # type: (click.Context, click.Parameter, Union[str, TextIO]) -> Optional[str]
    if not value:
        root_path = ctx.params.get("repo_path", None)
        if not root_path:
            root_path = "."
        root_path = pathlib.Path(root_path).resolve()
        config_path = root_path / "pyproject.toml"
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


def configure_regexes_from_args(args, default_regexes):
    # type: (OptionsDict, PatternDict) -> PatternDict
    regexes = {}
    if args["regex"]:
        if args["default_regexes"]:
            regexes.update(default_regexes)
        # FIXME: git_rules(_repo) functionality was never called, nor tested.
        #   https://github.com/godaddy/tartufo/issues/17 added for a new feature
        rules_files = cast(Tuple[TextIO, ...], args["rules"])
        if rules_files:  # or (args.git_rules_repo and args.git_rules):
            # if args.git_rules_repo and args.git_rules:
            #     configure_regexes_from_git(args.git_rules_repo, args.git_rules, rules_regexes)
            if rules_files:
                for rules_file in rules_files:
                    loaded = load_rules_from_file(rules_file)
                    dupes = set(loaded.keys()).intersection(regexes.keys())
                    if dupes:
                        raise ValueError(
                            "Rule(s) were defined multiple time: {}".format(dupes)
                        )
                    regexes.update(loaded)
    return regexes


def configure_regexes_from_git(
    git_url, repo_rules_filenames, rules_regexes
):  # pylint: disable=unused-argument
    # type: (str, List[str], PatternDict) -> PatternDict
    # FIXME: This was never called or tested.
    #  https://github.com/godaddy/tartufo/issues/17 has been added for tracking
    rules_project_path = util.clone_git_repo(git_url)
    try:
        # rules_filenames = [os.path.join(rules_project_path, repo_rules_filename)
        #                    for repo_rules_filename in repo_rules_filenames]
        return {}  # configure_regexes_from_rules_files(rules_filenames, rules_regexes)
    finally:
        shutil.rmtree(rules_project_path)


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
