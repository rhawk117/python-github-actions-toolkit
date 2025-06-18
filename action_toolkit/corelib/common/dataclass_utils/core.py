'''
action_toolkit.internals.dataclass_utils
'''

from collections.abc import Callable, Iterable, Iterator
from typing import TYPE_CHECKING, Any, TypeVar
import json
import dataclasses


from action_toolkit.corelib.common.dataclass_utils.types import JSONDumpOptions


if TYPE_CHECKING:
    from .options import DataclassConfig


def asdict_iterator(
    data_cls: Any,
    *,
    options: DataclassConfig
) -> Iterable[tuple[str, Any]]:
    '''
    Iterate over the fields of a dataclass as a key-value pairs,
    applying the provided filters and key aliasing defined in
    DataclassConfig.

    Parameters
    ----------
    data_cls : Any
        The dataclass instance to
        iterate over.
    options : DataclassConfig
        The options to apply for filtering and aliasing.
    Returns
    -------
    Iterable[tuple[str, Any]]
        An iterable of key-value pairs representing the fields and their values,
        filtered according to the options.

    Example
    -------
    ```python
    data_cls = MyDataclass(snake_cased='foo', none_field=None, bar='baz)
    options = DataclassConfig(
        exclude_none=True,
        exclude={'bar'},
        alias_generator=AliasType.CAMEL
    )
    print(asdict_iterator(data_cls, options))
    [('snakeCased', 'foo')]
    ```
    '''
    data_cls_items = dataclasses.asdict(data_cls).items()
    filter_fn = options.create_filter()
    alias_mapper = options.alias_mapper()

    if filter_fn:
        data_cls_items = filter(filter_fn, data_cls_items)

    if alias_mapper:
        data_cls_items = map(alias_mapper, data_cls_items)

    yield from data_cls_items



def dump(
    data_cls: Any,
    *,
    options: DataclassConfig | None = None
) -> dict[str, Any]:
    '''Convert a dataclass to a dictionary with options to exclude fields.

    Parameters
    ----------
    data_cls : Any
        The dataclass instance to convert, asdict will fail if not a dataclass.
    options : DataclassConfig | None, optional
        Options for filtering and aliasing the dataclass fields.
        If None, no options are applied (default is None).
    '''
    if not options:
        return dataclasses.asdict(data_cls)
    return dict(asdict_iterator(data_cls, options=options))


def json_dumps(
    data_cls: Any,
    *,
    options: DataclassConfig | None = None,
    json_args: JSONDumpOptions | None = None
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
    if not json_args:
        return json.dumps(
            dump(data_cls, options=options),
        )
    return json.dumps(
        dump(data_cls, options=options),
        **json_args
    )



__all__ = [
    'asdict_iterator',
    'dump',
    'json_dumps'
]






