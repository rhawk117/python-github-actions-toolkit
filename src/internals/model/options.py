from __future__ import annotations

from collections.abc import Callable
from typing import Any,  TypedDict


class DataclassInit(TypedDict, total=False):
    '''typed dictionary for the dataclass decorator options.'''
    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool
    match_args: bool
    kw_only: bool
    slots: bool


class ModelConfig:
    """Configuration class for SwiftexModel behavior, similar to Pydantic's ConfigDict.

    This class centralizes all configuration options for SwiftexModel instances,
    providing type safety and clear organization of settings.
    """

    __slots__ = (
        'dataclass_override',
        'alias_generator',
        'exclude_none',
        'json_indent',
        'json_default_handler',
        'validate_assignment',
        'use_enum_values',
        'deep_conversion',
        'max_recursion_depth'
    )

    def __init__(
        self,
        *,
        dataclass_override: DataclassInit | None = None,
        alias_generator: Callable[[str], str] | None = None,
        exclude_none: bool = False,
        json_indent: int = 0,
        max_recursion_depth: int = 100,
        json_default_handler: Callable[[Any], Any] = str,
        deep_conversion: bool = True,
        validate_assignment: bool = False,
        use_enum_values: bool = False
    ) -> None:
        """Initialize the ModelConfig with default or provided values."""
        self.dataclass_override: DataclassInit = dataclass_override or {}
        self.alias_generator: Callable[[str], str] | None = alias_generator
        self.exclude_none: bool = exclude_none
        self.max_recursion_depth: int = max_recursion_depth
        self.json_indent: int = json_indent
        self.deep_conversion: bool = deep_conversion
        self.json_default_handler: Callable[[Any], Any] = str
        self.validate_assignment: bool = validate_assignment
        self.use_enum_values: bool = use_enum_values
        self.json_default_handler = json_default_handler