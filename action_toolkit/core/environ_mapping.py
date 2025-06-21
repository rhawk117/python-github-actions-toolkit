

from ast import Call
import contextlib
import json
import os
from pathlib import Path
from turtle import st
from typing import Any, Self, TypeVar
from collections.abc import Callable, Generator, Iterator, Mapping


BOOLEAN_TRUE = frozenset(['true', 'yes', 'on', 'y', '1'])
BOOLEAN_FALSE = frozenset(['false', 'no', 'off', 'n', '0'])

T = TypeVar('T')


def _parse_bool(default: bool) -> Callable[[str], bool]:
    """
    Get a boolean input from environment variables.

    Parameters
    ----------
    key : str
        The input key to retrieve.
    default : bool, optional
        Default value if the input is not set (default is False).

    Returns
    -------
    bool
        The boolean value of the input.
    """

    def _resolve_bool(value: str | None) -> bool:
        if not value or not value.strip():
            return False

        value = value.lower().strip()
        if value in BOOLEAN_TRUE:
            return True
        elif value in BOOLEAN_FALSE:
            return False
        else:
            raise ValueError(f"Invalid boolean value: {value}")

    return _resolve_bool

def _json_parser(**json_kwargs: Any) -> Callable[[str], Any]:
    """
    Create a function to parse JSON from a string.

    Parameters
    ----------
    **json_kwargs : Any
        Additional keyword arguments to pass to json.loads.

    Returns
    -------
    Callable[[str], Any]
        A function that takes a string and returns the parsed JSON.
    """
    def loads_json(value: str) -> Any:
        return json.loads(value, **json_kwargs)

    return loads_json

def _multiline_parser(
    trim_whitespace: bool = True,
    skip_empty: bool = True
) -> Callable[[str], list[str]]:

    def parse_multiline(value: str | None) -> list[str]:
        """
        Parse a multiline input from environment variables.

        Parameters
        ----------
        value : str | None
            The input value to parse.

        Returns
        -------
        list[str]
            A list of lines from the input value.
        """
        if not value:
            return []

        if trim_whitespace:
            value = value.strip()

        lines = value.splitlines()
        if skip_empty:
            lines = [line for line in lines if line.strip()]
        return lines

    return parse_multiline


def _splittable_parser(
    delimiter: str = os.linesep,
    trim_whitespace: bool = True
) -> Callable[[str], list[str]]:

    def parse_splittable(value: str | None) -> list[str]:
        if not value:
            return []

        splitted = value.split(delimiter)
        if not trim_whitespace:
            return splitted

        return [
            part.strip() for part in value.split(delimiter)
            if part.strip()
        ]

    return parse_splittable


def _pathlike_parser(value: str | None) -> Path:
    """
    Parse a path-like input from environment variables.

    Parameters
    ----------
    value : str | None
        The input value to parse.

    Returns
    -------
    Path
        A Path object representing the input value.
    """
    if not value:
        return Path()

    return Path(value).expanduser().resolve()


def _try_cast(value: str | None, caster: Callable[[str], T],) -> T | None:
    """
    Try to get an environment variable by key.

    Parameters
    ----------
    key : str
        The environment variable key to retrieve.
    default : str | None, optional
        Default value to return if the key is not found.

    Returns
    -------
    str | None
        The value of the environment variable or default if not found.
    """

    if not value:
        return None

    try:
        return caster(value)
    except Exception as e:
        raise ValueError(
            f"Failed to cast {value} to type '{caster.__name__}"
        ) from e

def key_required(key: str) -> KeyError:
    return KeyError(
        f"Key '{key}' is required but could not be found."
    )


class EnvUtils:

    @staticmethod
    @contextlib.contextmanager
    def scoped_env(**kwargs: Any) -> Generator[None, None, None]:
        """
        Context manager to temporarily set environment variables.

        Parameters
        ----------
        **kwargs : Any
            Key-value pairs to temporarily set in the environment variables.

        Yields
        ------
        None
        """
        original = os.environ.copy()
        os.environ.update(kwargs)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(original)

    @staticmethod
    def update_env(items: Mapping[str, Any], prefix: str | None = None) -> None:
        """
        Update the environment variables with a dictionary of key-value pairs.

        Parameters
        ----------
        items : Mapping[str, Any]
            The items to update in the environment variables.
        prefix : str | None, optional
            The prefix to apply to the keys (default is None).
        """
        if prefix:
            items = {f"{prefix}_{k}": v for k, v in items.items()}
        os.environ.update(items)

    @staticmethod
    def env_items(*, prefix: str | None = None) -> Iterator[tuple[str, str]]:
        """
        Get environment variables filtered by a given prefix.

        Parameters
        ----------
        prefix : str | None
            The prefix to filter environment variables by.

        Returns
        -------
        Iterator[tuple[str, str]]
            An iterator over the filtered environment variables.
        """
        if prefix:
            yield from filter(
                lambda item: item[0].startswith(prefix),
                os.environ.items()
            )
        else:
            yield from os.environ.items()


    @staticmethod
    def iter_pathenv() -> Iterator[Path]:
        if 'PATH' not in os.environ:
            raise KeyError("Environment variable 'PATH' is not set.")

        path_env = os.environ['PATH']
        for path_str in path_env.split(os.pathsep):
            path_str = path_str.strip()
            if not path_str:
                continue
            resolved_path = _try_cast(
                path_str,
                caster=_pathlike_parser
            )
            yield resolved_path or Path(path_str)

    @staticmethod
    def filter(func: Callable[[str, str], bool]) -> Iterator[tuple[str, str]]:
        """
        Filter environment variables by a given function.

        Parameters
        ----------
        func : Callable[[str, str], bool]
            filter function accepting a key and value,
        Returns
        -------
        Iterator[tuple[str, str]]
            An iterator over the filtered environment variables.
        """
        yield from filter(lambda kv: func(kv[0], kv[1]), os.environ.items())

    @staticmethod
    def map(func: Callable[[str, str], T]) -> Iterator[T]:
        """
        Map a function over environment variables.

        Parameters
        ----------
        func : Callable[[str, str], T]
            map function accepting a key and value,

        Returns
        -------
        Iterator[T]
            An iterator over the transformed values.
        """
        yield from map(lambda kv: func(kv[0], kv[1]), os.environ.items())



class EnvDict:
    def __init__(
        self,
        *,
        prefix: str | None = None,
        items: Mapping[str, Any] | None = None
    ) -> None:
        """
        Initialize an EnvDict instance.

        Parameters
        ----------
        prefix : str
            The prefix for the environment variables.
        items : Mapping[str, Any] | None, optional
            Initial items to populate the dictionary (default is None).
        """
        self.prefix = prefix
        self._items = items or {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get an item from the environment dictionary.

        Parameters
        ----------
        key : str
            The key to retrieve.
        default : Any, optional
            Default value if the key is not found (default is None).

        Returns
        -------
        Any
            The value associated with the key or default if not found.
        """
        return self._items.get(f"{self.prefix}_{key}", default)

    def contains(self, key: str) -> bool:
        """
        Check if the environment dictionary contains a key.

        Parameters
        ----------
        key : str
            The key to check.

        Returns
        -------
        bool
            True if the key exists, False otherwise.
        """
        return f"{self.prefix}_{key}" in self._items

    def get_pathlike(
        self,
        key: str,
        *,
        default: Path | None = None,
        required: bool = False
    ) -> Path | None:
        if key not in self._items:
            if required:
                raise key_required(key)
            return default or Path()

        return _try_cast(
            self._items[key],
            caster=_pathlike_parser
        ) or default


    def get_int(
        self,
        key: str,
        *,
        default: int = 0,
        required: bool = False
    )-> int:
        """
        Get an integer input from environment variables.

        Parameters
        ----------
        key : str
            The input key to retrieve.
        default : int, optional
            Default value if the input is not set or cannot be converted (default is 0).

        Returns
        -------
        int
            The integer value of the input.
        """
        if key not in self._items:
            if required:
                raise key_required(key)
            return default

        return _try_cast(
            self._items[key],
            caster=int
        ) or default


    def get_bool(
        self,
        key: str,
        *,
        required: bool = False,
        default: bool = False
    ) -> bool:
        if key not in self._items:
            if required:
                raise key_required(key)
            return default

        return _try_cast(
            self._items[key],
            caster=_parse_bool(default)
        ) or default


    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Gets a key from environment variables and
        casts it to a float.

        Parameters
        ----------
        key : str
            The input key to retrieve.
        default : float, optional
            Default value if the input is not set or cannot be converted (default is 0.0).

        Returns
        -------
        float
            The float value of the input.
        """
        if key not in self._items:
            return default

        return _try_cast(
            self._items[key],
            caster=float
        ) or default


    def get_json(
        self,
        key: str,
        default: Any = None,
        **json_kwargs: Any
    ) -> Any:
        """
        Get a JSON input from environment variables.

        Parameters
        ----------
        key : str
            The input key to retrieve.
        default : Any, optional
            Default value if the input is not set or cannot be parsed (default is None).

        Returns
        -------
        Any
            The parsed JSON value of the input.
        """
        if key not in self._items:
            return default

        return _try_cast(
            self._items[key],
            caster=_json_parser(**json_kwargs)
        ) or default


    def get_multiline(
        self,
        key: str,
        *,
        required: bool = False,
        default: list[str] = [],
        trim_whitespace: bool = True,
        skip_empty_lines: bool = True
    ) -> list[str]:
        """
        Get a multiline input from environment variables.

        Parameters
        ----------
        key : str
            The input key to retrieve.
        trim_whitespace : bool, optional
            Whether to trim whitespace from each line (default is True).
        skip_empty_lines : bool, optional
            Whether to skip empty lines (default is True).

        Returns
        -------
        list[str]
            A list of lines from the input value.
        """
        if key not in self._items:
            if required:
                raise key_required(key)
            return default or []
        return _try_cast(
            self._items[key],
            caster=_multiline_parser(
                trim_whitespace=trim_whitespace,
                skip_empty=skip_empty_lines
            ),
        ) or default


    def get_splittable(
        self,
        key: str,
        *,
        delimiter: str = os.linesep,
        trim_whitespace: bool = True
    ) -> list[str]:
        """
        Get a splittable input from environment variables.

        Parameters
        ----------
        key : str
            The input key to retrieve.
        delimiter : str, optional
            The delimiter to split the input value (default is os.linesep).
        trim_whitespace : bool, optional
            Whether to trim whitespace from each part (default is True).

        Returns
        -------
        list[str]
            A list of parts from the input value.
        """
        return _try_cast(
            self._items.get(key),
            caster=_splittable_parser(
                delimiter=delimiter,
                trim_whitespace=trim_whitespace
            )
        ) or []


    @classmethod
    def prefixed_by(cls, prefix: str) -> Self:
        prefixed_items = EnvUtils.filter(
            lambda k, _: k.startswith(prefix)
        )
        return cls(
            prefix=prefix,
            items=dict(prefixed_items)
        )


'''

# Built in type support for,
# str, int, float, bool, Path, datetime, list[str], dict[str, Any]

class EnvironConfig:
    ...

# Automatically loads environment variables from os.environ or a .env file
class FooVar(EnvironModel)
    config = EnvironConfig(
        prefix='FOO_'
    )

    bar: Annotated[str, EnvDef(
        ..., # "required"
        default='default_value',
        default_factory=None
    )] # In environ as 'FOO_BAR', alias defaults to attribute name

    bar_date: Annotated[datetime, EnvDef(
        default=None,
        alias='DATE', #
        caster=lambda v: datetime.fromisoformat(v) # applied only if value is not None
    )] # resolves to simply 'FOO_BAR_DATE' in environ

    baz: Annotated[int, EnvDef(
        default=0
    )]

# or also....

class FooVar(EnvironModel):
    config = EnvironConfig(
        prefix='FOO_',
        file='.env'
        encoding='utf-8'
    )

    bar: str = desc(
        ...,  # "required" field
        default='default_value',
        default_factory=None
    )  # In .env as 'FOO_BAR', alias defaults to attribute name


# if you create an instance without a required field, it will raise an error


To resolve github action inputs...

# Built in type support for,
# str, int, float, bool, Path, datetime, list[str], dict[str, Any]

class Inputs(ActionInputs):
    api_url: str = action_input(
        yaml_alias='api-url', # which on runner is 'INPUTS_API_URL'
        transformer=lambda v: v.strip() if v else None,
    )




'''