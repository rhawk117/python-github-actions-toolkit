from __future__ import annotations

import json
import os
from pathlib import Path
from collections.abc import Callable, Generator
from typing import (
    Any,
    ClassVar,
    Generic,
    Protocol,
    TypeVar,
)

T = TypeVar("T")


class ParsableType(Protocol[T]):
    """Two simple static methods for (de)serialising one type."""

    @staticmethod
    def parse(raw: str) -> T: ...          # noqa: D401

    @staticmethod
    def serialize(value: T) -> str: ...    # noqa: D401


class _TypeHandler(Generic[T]):
    """Internal wrapper so we can also accept plain callables."""

    def __init__(self, parse: Callable[[str], T], ser: Callable[[T], str]) -> None:
        self.parse = parse
        self.serialize = ser


# built-ins

def _bool_parse(s: str) -> bool:
    '''parses a string into a boolean value.'''
    return s.lower() in {"1", "true", "yes", "on"}


def _list_parser(s: str) -> list[str]:
    '''reads comma-separated string into a list'''
    return [x.strip() for x in s.split(",") if x.strip()]

def _list_serializer(xs: list[str]) -> str:
    '''default serializer for lists of strings.'''
    return ",".join(map(str, xs))


_HANDLERS: dict[type, _TypeHandler[Any]] = {
    str: _TypeHandler(str, str),
    int: _TypeHandler(int, str),
    float: _TypeHandler(float, str),
    bool: _TypeHandler(_bool_parse, lambda b: "true" if b else "false"),
    list: _TypeHandler(_list_parser,  _list_serializer),
    dict: _TypeHandler(json.loads, json.dumps),
    Path: _TypeHandler(Path, str),
}

def iter_handlers() -> Generator[tuple[type, _TypeHandler[Any]], None, None]:
    '''Iterates over the key value pairs of handler, should never
    be used externally unless debugging.

    Yields
    ------
    Generator[tuple[type, _TypeHandler[Any]], None, None]
        _description_
    '''
    for type_, handler in _HANDLERS.items():
        yield type_, handler


