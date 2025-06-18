

from collections.abc import Callable
import json
from typing import Any, Literal, TypeAlias, TypedDict


AliasFn: TypeAlias = Callable[[str], str]
FilterFn: TypeAlias = Callable[[tuple[str, Any]], bool]
AliasMapFn: TypeAlias = Callable[[tuple[str, Any]], tuple[str, Any]]
AliasTypes: TypeAlias = Literal['snake', 'camel', 'kebab', 'pascal']


class JSONLoadOptions(TypedDict, total=False):
    '''
    TypedDict for JSON load options.
    '''

    object_hook: Callable[[dict[str, Any]], Any] | None
    parse_float: Callable[[str], float] | None
    parse_int: Callable[[str], int] | None
    parse_constant: Callable[[str], Any] | None
    cls: type[json.JSONDecoder] | None

class JSONDumpOptions(TypedDict, total=False):
    '''
    TypedDict for JSON dump options.
    '''

    skipkeys: bool
    ensure_ascii: bool
    check_circular: bool
    allow_nan: bool
    cls: type[json.JSONEncoder] | None
    indent: None | int | str
    separators: tuple[str, str] | None
    default: Callable[[Any], Any] | None
    sort_keys: bool
