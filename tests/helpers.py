from dataclasses import fields
from typing import Type, TypeVar

OptionsType = TypeVar("OptionsType")


def generate_options(option_class: Type[OptionsType], **kwargs) -> OptionsType:
    option_args = {field.name: None for field in fields(option_class)}
    option_args.update(kwargs)
    return option_class(**option_args)  # type: ignore
