"""
**meta_data.py**

Provides a wrapper around `dataclasses.field` to add metadata and extended functionality
to the fields of a dataclass. This allows for additional attributes
like default values.

"""

from __future__ import annotations

import dataclasses

from typing import Any, TypeVar
from collections.abc import Callable, Mapping


T = TypeVar("T")
dataclassesMISSING = dataclasses.MISSING


def meta(
    *,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[[], Any] | None = None,
    desc: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    **dataclass_kwargs: Any,
) -> dataclasses.Field:
    """A wrapper around `dataclasses.field` that allows you to add
    additional metadata to the field with extended functionality.

    Parameters
    ----------
    default : Any, optional
        _default value_, by default dataclasses.MISSING

    default_factory : Callable[[], Any] | None, optional
        _fallback if not provided_, by default None

    desc : str | None, optional
        _description of the attribute_, by default None

    validate : Callable[[Any], Any] | None, optional
        _method to validate the the type_, by default None

    metadata : Mapping[str, Any] | None, optional
        extra data to add to the model metadata accessible
        via  __custom_flags___

    Returns
    -------
    Any
        _the extended dataclass field_
    """
    meta = dict(metadata or {})
    if desc:
        meta["desc"] = desc
    return dataclasses.field(  # hand-off to std-lib
        default=default,
        default_factory=default_factory,  # type: ignore[arg-type]
        metadata=meta,
        **dataclass_kwargs,
    )


@dataclasses.dataclass(slots=True, frozen=True)
class ModelOptions:
    frozen: bool | None = None
    slots: bool | None = None
    order: bool | None = None
    kw_only: bool | None = None

    exclude_none: bool = False
    serialization_alias_generator: Callable[[str], str] | None = None


DATACLASS_KWARGS = {
    "init",
    "repr",
    "eq",
    "order",
    "unsafe_hash",
    "frozen",
    "slots",
    "weakref_slot",
    "match_args",
    "kw_only",
}
