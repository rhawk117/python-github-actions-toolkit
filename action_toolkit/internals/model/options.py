from __future__ import annotations


from collections.abc import Callable
from typing import Any, TypedDict


class DataclassInit(TypedDict, total=False):
    """typed dictionary for the dataclass decorator options."""

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
    """An configuration class for customizing and overriding the default
    behavior of a model interface.

    Attributes
    ----------
    dataclass_init : DataclassInit | None, optional
            _parameters for the data class_, by default None

        alias_generator : Callable[[str], str] | None, optional
            _a function that is called if not none when .dump() is
            called on a model interface to transform the keys from the resulting
            dictionary, a common use case would be transforming class attribute names
            from snake case to camel case_, by default None

        exclude_none : bool, optional
            _whether to exclude none by default when dump() is called
            so you don't have to explicitly pass the flag each time you call it_,
            by default False


        json_indent : int, optional
            _the ident for json.dump()_, by default 0

        max_recursion_depth : int, optional
            _how many recursive calls are allowed when
            calling .dump(), recursive calls in the .dump() method
            are made for non-primitive types such as dictionaries,
            if you run into stack overflow errors, play with this parameter
            however also keep in mind that it might be better exclude the more
            nested parameters and parse them seperately for better performance_,
            by default 100

        json_default_handler : Callable[[Any], Any], optional
            _the default handler for calling the json_dumps() and json_loads()
            method_, by default str

        deep_conversion : bool, optional
            _specifies how the .dump() method handles class members that
            are ModelInterface, when true it'll call .dump() on the child
            class_, by default True

        custom_model_config : Any | None, optional
            _custom configurations for the model interface, this is not used by the
            ModelInfterface class itself, but you can use to create and define custom
            configurations for your model interface_

    """

    __slots__ = (
        'dataclass_init',
        'alias_generator',
        'populate_by_alias',
        'exclude_none',
        'max_recursion_depth',
        'json_default_handler',
        'deep_conversion',
    )

    def __init__(
        self,
        *,
        dataclass_init: DataclassInit | None = None,
        alias_generator: Callable[[str], str] | None = None,
        exclude_none: bool = False,
        max_recursion_depth: int = 100,
        json_default_handler: Callable[[Any], Any] = str,
        deep_conversion: bool = True,
        custom_model_config: Any | None = None,
    ) -> None:
        """Options to configure the behavior of a model interface.


        Parameters
        ----------
        dataclass_init : DataclassInit | None, optional
            _parameters for the data class_, by default None

        alias_generator : Callable[[str], str] | None, optional
            _a function that is called if not none when .dump() is
            called on a model interface to transform the keys from the resulting
            dictionary, a common use case would be transforming class attribute names
            from snake case to camel case_, by default None

        exclude_none : bool, optional
            _whether to exclude none by default when dump() is called
            so you don't have to explicitly pass the flag each time you call it_,
            by default False


        json_indent : int, optional
            _the ident for json.dump()_, by default 0

        max_recursion_depth : int, optional
            _how many recursive calls are allowed when
            calling .dump(), recursive calls in the .dump() method
            are made for non-primitive types such as dictionaries,
            if you run into stack overflow errors, play with this parameter
            however also keep in mind that it might be better exclude the more
            nested parameters and parse them seperately for better performance_,
            by default 100

        json_default_handler : Callable[[Any], Any], optional
            _the default handler for calling the json_dumps() and json_loads()
            method_, by default str

        deep_conversion : bool, optional
            _specifies how the .dump() method handles class members that
            are ModelInterface, when true it'll call .dump() on the child
            class_, by default True

        custom_model_config : Any | None, optional
            _custom configurations for the model interface, this is not used by the
            ModelInfterface class itself, but you can use to create and define custom
            configurations for your model interface_
        """
        self.dataclass_init: DataclassInit = dataclass_init or {}
        self.alias_generator: Callable[[str], str] | None = alias_generator
        self.populate_by_alias: bool = True
        self.exclude_none: bool = exclude_none
        self.max_recursion_depth: int = max_recursion_depth
        self.deep_conversion: bool = deep_conversion
        self.json_default_handler: Callable[[Any], Any] = json_default_handler
