from pathlib import Path
import platform
from dataclasses import fields
from typing import Type, TypeVar

WINDOWS = platform.system().lower() == "windows"
PY_VERSION = platform.python_version_tuple()
PY_36 = ("3", "6", "0") <= PY_VERSION < ("3", "7", "0")
PY_37 = ("3", "7", "0") <= PY_VERSION < ("3", "8", "0")
BROKEN_USER_PATHS = WINDOWS and (PY_36 or PY_37)
REPO_ROOT_PATH = Path(__file__).parent.parent
DATA_PATH = REPO_ROOT_PATH.joinpath("tests", "data")


OptionsType = TypeVar("OptionsType")  # pylint: disable=invalid-name


def get_data_path(*added_paths: str) -> Path:
    return Path.joinpath(DATA_PATH, *added_paths)


def generate_options(option_class: Type[OptionsType], **kwargs) -> OptionsType:
    option_args = {field.name: None for field in fields(option_class)}  # type: ignore [arg-type]
    option_args.update(kwargs)
    return option_class(**option_args)  # type: ignore
