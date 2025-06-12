

from collections.abc import Mapping, Callable
import os
import pprint
from typing import Any, overload, TypeVar
from .type_parsing import _HANDLERS, _TypeHandler

T = TypeVar('T')

def add_type_handler(
    type_: type[T],
    parse: Callable[[str], T],
    serialize: Callable[[T], str]
) -> None:
    '''Adds a custom type handler for parsing and serializing values

    Parameters
    ----------
    type_ : type[T]
        _the type being parsed_
    parse : Callable[[str], T]
        _the function called to parse the string into the input type_
    serialize : Callable[[T], str]
        _the function to turn the value into a string_
    '''
    _HANDLERS[type_] = _TypeHandler(parse, serialize)

def get_type_handler(type_: type[T]) -> _TypeHandler[T]:
    '''Returns the handler for the given type, or raises KeyError if not found.
    should never be used externally unless debugging.
    Parameters
    ----------
    type_ : type[T]
        _the type to get_

    Returns
    -------
    _TypeHandler[T]
        _the handler for the type_

    Raises
    ------
    KeyError
        _if a key for the type does not exist_
    '''
    handler = _HANDLERS.get(type_)
    if handler is None:
        raise KeyError(f"CodecsError: No handler registered for type {type_.__name__}")
    return handler


class EnvironmentVariables:
    '''A wrapper for environment variables that allows for type casting
    and prefixing keys, implemented instead of python-dotenv to avoid
    using external dependencies.
    '''
    def __init__(
        self,
        *,
        env: Mapping[str, str] | None = None,
        prefix: str = ""
    ) -> None:
        self._env: Mapping[str, str] = dict(env or os.environ)
        self._prefix: str = prefix

    @overload
    def get(
        self,
        key: str,
        *,
        cast_to: type[T] = str,
        default: T,
        auto_error: bool = True,
    ) -> T: ...

    @overload
    def get(
        self,
        key: str,
        *,
        cast_to: type[T] = str,
        default: None = None,
        auto_error: bool = True,
    ) -> T: ...

    def get(
        self,
        key: str,
        *,
        cast_to: type[T] = str,
        default: Any = None,
        auto_error: bool = True,
    ) -> T | None:
        '''Retrieves an environment variable by key, with optional type casting,

        Parameters
        ----------
        key : str
            _the key to get from the environment_
        cast_to : type[T], optional
            _the type to cast to_, by default str
        default : Any, optional
            _fallback value if the type parsing fails or key doesn't exist_, by default None
        auto_error : bool, optional
            _raises if the key doesnt exist or the type conversion fails_, by default True

        Returns
        -------
        T | None
            _the target type_

        Raises (when auto_error is True)
        ------
        KeyError
            _the key doesnt exist_
        ValueError
            _the type conversion fails_
        '''
        full = f"{self._prefix}{key}"
        raw = self._env.get(full)
        if raw is None:
            if auto_error and default is None:
                raise KeyError(f"{full} not set")
            return default
        try:
            codec = get_type_handler(cast_to)
            return codec.parse(raw)
        except Exception as exc:
            if auto_error and default is None:
                raise ValueError(f"EnvironmentVariablesError: {full} cannot cast to {cast_to}") from exc
            return default

    @classmethod
    def export_env(
        cls,
        env_file: str,
        *,
        env_vars: Mapping[str, Any],
        prefix: str = ""
    ) -> None:
        '''Export environment variables to a file given a mapping of variables
        and an optional prefix to add to each key in the mapping.

        Parameters
        ----------
        env_file : str
            _the environment file_
        env_vars : Mapping[str, str]
            _the mapping of variables_
        prefix : str, optional
            _description_, by default ""
        '''
        exported = []
        for key, value in env_vars.items():
            full_key = f"{prefix}{key}"
            if isinstance(value, str):
                exported.append(f"{full_key}={value}")
            else:
                codec = get_type_handler(type(value))
                exported.append(f"{full_key}={codec.serialize(value)}")

        with open(env_file, mode='a') as f:
            f.write("\n".join(exported) + "\n")

    @classmethod
    def pprint(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        indent: int = 2,
        env_prefix: str | None = None,
    ) -> None:
        '''Prints the environment variables in a pretty format.

        Parameters
        ----------
        env : Mapping[str, str] | None, optional
            _the environment to print_, by default None (uses os.environ)
        indent : int, optional
            _the indentation level_, by default 2
        env_prefix : str | None, optional
            _the prefix to add to each key_, by default None
        '''
        env = env or os.environ
        prefix = env_prefix or ""
        for key, value in sorted(env.items()):
            pprint.pprint(
                {f"{prefix}{key}": value},
                indent=indent,
                width=80,
                compact=True
            )
