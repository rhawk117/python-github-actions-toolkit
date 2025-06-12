from __future__ import annotations
import json

from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass, fields, asdict, replace
from typing import Any, Self, TypeVar, ClassVar

from .options import ModelConfig
from pydantic import BaseModel

# error for custom exception later
def use_alias_when_not_defined_err() -> str:
    return (
        'ModelInterfaceError: a class method with was called with use_alias flag set to True, but'
        'no alias_generator is defined in the model_config. Did you'
        'forget to set your alias generator in the model_config?'
    )

def attr_doesnt_exist_err(attr_name: str) -> str:
    return (
        f'ModelInterfaceError: the attribute "{attr_name}" does not exist in the model.'
        ' Did you forget to define it or was this a typo?'
    )





T = TypeVar('T', bound='ModelInterface')

class ModelInterface(metaclass=ModelInterfaceMeta):
    '''An Enhanced dataclass wrapper with comprehensive configuration support and
    extensive built in utility for for data manipulation, serialization,
    and validation. Configuration is managed through the model_config class variable,
    which supports dataclass options, serialization settings, and custom behaviors.

    Use the model_config class variable to configure the model's behavior.
    class ScreamingModel(ModelInterface):
        model_config = ModelConfig(
            alias_generator=lambda x: x.upper()
        )
    '''

    model_config: ClassVar[ModelConfig] = ModelConfig()


    def get_model_config(self) -> ModelConfig:
        """Returns the model's configuration object.

        This method retrieves the model_config class variable,
        which contains all configuration settings for the model.
        """
        return self.__class__.model_config


    def _get_alias_fn(self, use_alias_flag: bool) -> Callable[[str], str] | None:
        '''Returns the alias generator function if it is defined in the model_config
        or None if use_alias_flag is False.

        Arguments:
            use_alias_flag -- _the flag parameter of the caller_

        Raises:
            ValueError: if use_alias_flag is True and the alias_generator is not defined

        Returns:
            the alias generator function
        '''
        if not use_alias_flag:
            return None
        alias_fn = self.get_model_config().alias_generator
        if alias_fn is None:
            raise ValueError(
                use_alias_when_not_defined_err()
            )
        return alias_fn


    @classmethod
    def load(
        cls,
        data: dict[str, Any],
        *,
        strict: bool = False
    ) -> Self:
        '''Loads a class instance from a dictionary of
        key word arguments.

        Arguments:
            cls -- _class_ of the instance to create
            data -- dictionary of key word arguments to use for the instance

        Keyword Arguments:
            strict -- forbids extra keys in the data dict (default: {False}):

        Raises:
            TypeError: if strict is True and the data dict contains keys that are not

        Returns:
            the class instance
        '''
        allowed = {f.name for f in fields(cls)}
        extras = data.keys() - allowed
        if strict and extras:
            raise TypeError(f"{cls.__name__}.load() got unexpected keys: {extras}")

        return cls(**{k: v for k, v in data.items() if k in allowed})


    @classmethod
    def json_loads(
        cls,
        json_str: str,
        *,
        strict: bool = True
    ) -> Self:
        '''Loads a class instance from a JSON string.

        Arguments:
            cls -- _class_ of the instance to create
            json_str -- _JSON string to load_

        Returns:
            _the class instance_
        '''
        data = json.loads(json_str)
        return cls.load(data, strict=strict)


    def dump(
        self,
        *,
        deep: bool | None = None,
        exclude_none: bool | None = None,
        exclude: set[str] | None = None,
        use_alias: bool = False
    ) -> dict[str, Any]:
        '''Returns the class instance as a dictionary with optional options.

        Keyword Arguments:
            deep -- for deep recursion (default: {None})
            exclude_none -- exclude attributes with None (default: {None})
            exclude -- attribute names to exclude (default: {None})
            use_aliases -- use the alias generator to generate the dictionary keys
            from the model config (default: {False})

        Returns:
            A dictionary representation of the class instance,
            with options applied.
        '''
        config = self.get_model_config()

        if deep is None:
            deep = config.deep_conversion

        if exclude_none is None:
            exclude_none = config.exclude_none

        def _convert(value: Any) -> Any:
            if deep and isinstance(value, ModelInterface):
                return value.dump(
                    deep=True,
                    exclude_none=exclude_none,
                    exclude=exclude,
                    use_alias=use_alias
                )

            if deep and isinstance(value, (list, tuple, set)):
                return [_convert(v) for v in value]

            if deep and isinstance(value, dict):
                return {k: _convert(v) for k, v in value.items()}

            return value

        data: dict[str, Any] = {}
        alias_fn = self._get_alias_fn(use_alias)
        for attr, value in asdict(self).items():
            if exclude and attr in exclude:
                continue
            if exclude_none and value is None:
                continue
            key = alias_fn(attr) if alias_fn else attr
            data[key] = _convert(value)

        return data


    def json_dumps(
        self,
        *,
        indent: int | None = None,
        deep: bool | None = None,
        exclude_none: bool | None = None,
        exclude: set[str] | None = None,
        use_alias: bool = False,
        **json_kwargs
    ) -> str:
        '''Returns the class instance as a JSON string with optional options
        for serialization and the format of the output.

        Keyword Arguments:
            indent -- the json indent (default: {None})
            deep -- deep recursion (default: {None})
            exclude_none -- to exclude none (default: {None})
            exclude -- attributes to exclude / not include (default: {None})
            use_alias -- apply alias generator to dictionary keys (default: {False})

        Returns:
            A JSON string representation of the class instance
        '''
        config = self.get_model_config()

        if indent is None:
            indent = config.json_indent

        default_handler = config.json_default_handler

        return json.dumps(
            self.dump(
                deep=deep,
                exclude_none=exclude_none,
                exclude=exclude,
                use_alias=use_alias
            ),
            indent=indent,
            default=default_handler,
            **json_kwargs
        )


    def copy(self, **changes: Any) -> Self:
        '''Creates a modified copy of the class instance using
        dataclass libraries replace function.

        Args:
            **changes: the field changes to apply to the new instance

        Returns:
            New instance with specified changes applied to field values

        Arguments:
            self -- _description_

        Returns:
            _description_
        '''
        return replace(self, **changes)


    def diff(self, other: Self) -> dict[str, tuple[Any, Any]]:
        '''_Compares the calling class instance to another instance of the same class
        and performs field-by-field comparison between two instances
        of the same type, returning detailed information about value differences._

        Args:
            other: _The other class instance of the same model / class type
            for comparison_

        Returns:
            dict[str, tuple[Any, Any]] -- _dictionary mapping field names to tuples of
            (self_value, other_value) for fields that differ between instances_
        Raises:
            TypeError: _when comparing instances of different types_
        '''
        if type(self) is not type(other):
            raise TypeError("diff() expects an instance of the same type")

        out: dict[str, tuple[Any, Any]] = {}
        for f in fields(self):
            a, b = getattr(self, f.name), getattr(other, f.name)
            if a != b:
                out[f.name] = (a, b)
        return out


    def attrs(
        self,
        *,
        exclude_none: bool = False,
        exclude: set[str] | None = None,
        use_alias: bool = False
    ) -> Generator[tuple[str, Any], None, None]:
        '''_A generator for iterating over a class instances
        attribute name and value with options to filter the
        output_

        Keyword Arguments:
            exclude_none -- _exclude an attribute if it's none_ (default: {False})
            exclude -- _attribute names to exclude from being yielded_ (default: {None})

        Yields:
            _the attribute name and attribute value_
        '''
        alias_fn = self._get_alias_fn(use_alias)
        for f in fields(self):
            if exclude and f.name in exclude:
                continue
            value = getattr(self, f.name)
            if exclude_none and value is None:
                continue
            attr_name = alias_fn(f.name) if alias_fn else f.name
            yield attr_name, value


    def map_attrs(
        self,
        map_func: Callable[[str, Any], Any]
    ) -> Generator[Any, None, None]:
        '''Maps a function over the attributes of the class instance,
        the attribute name passed is not the alias.

        Arguments:
            map_func -- _the map function with (attr_name, attr_value)_

        Yields:
            _the result of the map function_
        '''
        for f in fields(self):
            yield map_func(f.name, getattr(self, f.name))

    def filter_attrs(
        self,
        filter_func: Callable[[str, Any], bool]
    ) -> Generator[tuple[str, Any], None, None]:
        '''Filters the attributes of the class instance using a filter function.

        Arguments:
            filter_func -- _the filter function with (attr_name, attr_value)_

        Yields:
            _the attribute name and value for attributes that pass the filter_
        '''
        for f in fields(self):
            value = getattr(self, f.name)
            if filter_func(f.name, value):
                yield f.name, value


    def set_attr(self, name: str, value: Any) -> None:
        '''Sets a field value by name, raises AttributeError if the field does not exist.

        Arguments:
            name -- _the attribute / field name_
            value -- _the attribute value_

        Raises:
            AttributeError: _if the attribute doesn't exist_
        '''
        if not hasattr(self, name):
            raise AttributeError(attr_doesnt_exist_err(name))

        setattr(self, name, value)


    def get_attr(self, name: str, default: Any | None = None) -> Any | None:
        '''gets a field value by name, returns default if the field does not exist.

        Arguments:
            name -- _the attribute / field name_

        Keyword Arguments:
            default -- _the default value_ (default: {None})

        Returns:
            _the resulting value_
        '''
        return getattr(self, name, default)


    def as_str(self) -> str:
        '''Creates a string representation of the class instance,
        including all attributes and their values in a formatted string.

        Returns:
            _the string representation of the class_
        '''
        attr_str = ", ".join(
            f"{f.name}={getattr(self, f.name)!r}"
            for f in fields(self)
        )
        return f"{self.__class__.__name__}<{attr_str}>"


    def get_field_aliases(self) -> dict[str, str]:
        '''Returns a dictionary mapping field names to their aliases,
        useful for debugging

        Returns:
            _A dictionary with the key being the attribute name and the
            value being the attribute alias_
        '''
        alias_fn = self._get_alias_fn(use_alias_flag=True)
        return {
            f.name: alias_fn(f.name) if alias_fn else f.name
            for f in fields(self)
        }


    def __iter__(self) -> Iterator[Any]:
        '''Iterates over the class instance attributes and yields
        the values of the attributes.

        Yields:
            _the attribute value_
        '''
        yield from (getattr(self, f.name) for f in fields(self))


    def __str__(self) -> str:
        '''Returns a string representation of the class instance using the as_str method.

        Returns:
            _the string of the class_
        '''
        return self.as_str()