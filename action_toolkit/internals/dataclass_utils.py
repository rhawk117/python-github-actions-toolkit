'''
action_toolkit.internals.dataclass_utils
'''

from collections.abc import Iterable, Iterator
from typing import Any

import json
import dataclasses

def dump_dataclass(
    data_cls: Any,
    *,
    exclude_none: bool = False,
    exclude: set[str] | None = None
) -> dict[str, Any]:
    '''Convert a dataclass to a dictionary with options to exclude fields.

    Parameters
    ----------
    data_cls : BaseDataclass
        The dataclass instance to convert.
    exclude_none : bool, optional
        If True, exclude fields with None values (default is False).
    exclude : set[str] | None, optional
        A set of field names to exclude from the dictionary (default is None).
    '''
    dump = dataclasses.asdict(data_cls)
    if not exclude and not exclude_none:
        return dump

    for field in dataclasses.fields(data_cls):
        if exclude and field.name in exclude:
            dump.pop(field.name, None)

        elif exclude_none and dump.get(field.name) is None:
            dump.pop(field.name, None)

    return dump

def iter_dataclass_dict(
    data_cls: Any,
    *,
    exclude_none: bool = False,
    exclude: set[str] | None = None
) -> Iterable[tuple[str, Any]]:
    '''Iterate over the fields of a dataclass as key-value pairs.

    Parameters
    ----------
    cls : BaseDataclass
        The dataclass instance to iterate over.
    exclude_none : bool, optional
        If True, exclude fields with None values (default is False).
    exclude : set[str] | None, optional
        A set of field names to exclude from the iteration (default is None).

    Returns
    -------
    Iterable[tuple[str, Any]]
        An iterable of key-value pairs representing the fields and their values.
    '''
    for field in dataclasses.fields(data_cls):
        if exclude and field.name in exclude:
            continue
        value = getattr(data_cls, field.name, None)
        if exclude_none and value is None:
            continue
        yield field.name, value


def json_dumps_dataclass(
    data_cls: Any,
    *,
    exclude_none: bool = False,
    exclude: set[str] | None = None
) -> str:
    '''Convert a dataclass to a JSON string.

    Parameters
    ----------
    cls : BaseDataclass
        The dataclass instance to convert.
    exclude_none : bool, optional
        If True, exclude fields with None values (default is False).
    exclude : set[str] | None, optional
        A set of field names to exclude from the JSON output (default is None).

    Returns
    -------
    str
        A JSON string representation of the dataclass.
    '''

    return json.dumps(
        dump_dataclass(data_cls, exclude_none=exclude_none, exclude=exclude),
        indent=2
    )

def iter_dataclass(data_cls: Any) -> Iterator[tuple[str, Any]]:
    '''Iterate over the fields of a dataclass as key-value pairs.

    Parameters
    ----------
    cls : BaseDataclass
        The dataclass instance to iterate over.

    Returns
    -------
    Iterator[tuple[str, Any]]
        An iterator of key-value pairs representing the fields and their values.
    '''
    for field in dataclasses.fields(data_cls):
        yield field.name, getattr(data_cls, field.name, None)


