import dataclasses
from typing import TYPE_CHECKING, Any, Callable, TypedDict

from test.test_reprlib import r

from action_toolkit.corelib.common.dataclass_utils.types import AliasMapFn

from .alias import get_alias_generator

if TYPE_CHECKING:
    from .types import AliasTypes




class BaseConfig:
    '''
    Utility class for configuring a dataclass with options
    for serialization and filtering, used throughout dataclass_utils
    for what do with the output of dataclass serialization or `dataclasses.asdict()`.

    Attributes
    ----------
    exclude_none: bool
        If True, fields with None values are excluded from serialization.
    exclude: set[str] | None
        A set of field names to exclude from serialization.
    include: set[str] | None
        A set of field names to include in serialization. If None, all fields are included.
    alias_generator: AliasType | None
        The alias type to use for field names. If None, no aliasing is applied.
        Supported types are: snake, camel, kebab, and pascal.
    '''
    def __init__(
        self,
        *,
        alias_generator: AliasTypes | None = None,
        exclude: set[str] | None = None,
    ) -> None:
        self.alias_generator: AliasTypes | None = alias_generator
        self.exclude: set[str] | None = exclude

    def filters(self) -> list[Callable[[str, Any], bool]]:
        '''
        Create a filter function based on the provided options.

        Returns
        -------
        Callable[[str, Any], bool] | None
            A filter function that can be used with `filter()`, or None if no filtering is needed.
        '''
        filter_funcs = []
        if self.exclude:
            filter_funcs.append(
                lambda k, v: k not in self.exclude
            )
        return filter_funcs

    def create_filter(self) -> Callable[[tuple[str, Any]], bool]:
        '''
        Create a filter function that applies the filters defined in this options instance.

        Parameters
        ----------
        extras : list[Callable[[str, Any], bool]] | None
            Additional filter functions to apply. If None, only the filters defined in this instance are used.

        Returns
        -------
        Callable[[tuple[str, Any]], bool]
            A function that takes a key-value pair and returns True if it should be included.
        '''
        filter_funcs = self.filters()
        def _filter_func(kv_pair: tuple[str, Any]) -> bool:
            key, value = kv_pair
            return all(pred(key, value) for pred in filter_funcs)

        return _filter_func


    def alias_mapper(self) -> AliasMapFn | None:
        '''
        Create an alias mapping function based on the alias generator.

        Returns
        -------
        Callable[[tuple[str, Any]], tuple[str, Any]]
            A function that takes a key-value pair and returns a new key with the alias applied.
        '''
        if not self.alias_generator:
            return None
        alias_fn = get_alias_generator(self.alias_generator)
        if not alias_fn or not callable(alias_fn):
            raise ValueError(
                f'alias generator of type {self.alias_generator} is not callable.'
                'and cannot be applied to the dataclass.'
            )

        def _alias_mapper_fn(kv_pair: tuple[str, Any]) -> tuple[str, Any]:
            key, value = kv_pair
            return alias_fn(key), value
        return _alias_mapper_fn



class DataclassConfig(BaseConfig):
    '''
    Utility class for configuring a dataclass with options
    for serialization and filtering, used throughout dataclass_utils
    for what do with the output of dataclass serialization or `dataclasses.asdict()`.

    Attributes
    ----------
    exclude_none: bool
        If True, fields with None values are excluded from serialization.
    exclude: set[str] | None
        A set of field names to exclude from serialization.
    include: set[str] | None
        A set of field names to include in serialization. If None, all fields are included.
    alias_generator: AliasType | None
        The alias type to use for field names. If None, no aliasing is applied.
        Supported types are: snake, camel, kebab, and pascal.
    '''
    def __init__(
        self,
        *,
        exclude_none: bool = False,
        exclude: set[str] | None = None,
        include: set[str] | None = None,
        alias_generator: AliasTypes | None = None
    ) -> None:
        super().__init__(alias_generator=alias_generator)
        self.include: set[str] | None = include
        self.exclude_none: bool = exclude_none
        self.exclude: set[str] | None = exclude

    def filters(self) -> list[Callable[[str, Any], bool]]:
        '''
        Additional filters for the DataclassConfig class.

        Returns
        -------
        list[Callable[[str, Any], bool]]
            _callable filters_
        '''
        filter_funcs = super().filters()

        if self.exclude_none:
            filter_funcs.append(
                lambda k, v: v is not None
            )
        if self.include:
            filter_funcs.append(
                lambda k, v: k in self.include # type: ignore[return-value]
            )
        return filter_funcs





def create_config(
    *,
    exclude_none: bool = False,
    exclude: set[str] | None = None,
    include: set[str] | None = None,
    alias_generator: AliasTypes | None = None
) -> DataclassConfig:
    '''
    Create a DataclassConfig instance with the provided options.

    Parameters
    ----------
    exclude_none : bool, optional
        If True, fields with None values are excluded from serialization (default is False).
    exclude : set[str] | None, optional
        A set of field names to exclude from serialization (default is None).
    include : set[str] | None, optional
        A set of field names to include in serialization. If None, all fields are included (default is None).
    alias_generator : AliasTypes | None, optional
        The alias type to use for field names (default is None).

    Returns
    -------
    DataclassConfig
        An instance of DataclassConfig with the specified options.
    '''
    return DataclassConfig(
        exclude_none=exclude_none,
        exclude=exclude,
        include=include,
        alias_generator=alias_generator
    )

__all__ = [
    'DataclassConfig',
    'create_config'
]










