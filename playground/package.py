"""
Environment Variables SDK for GitHub Actions
Provides type-safe environment variable loading with dataclass integration.
"""

from __future__ import annotations

from pydantic_settings import SettingsConfigDict

import json
import os
import re

from dataclasses import MISSING, Field, dataclass, field
from datetime import datetime
from functools import cached_property
from pathlib import Path
import shlex
from types import EllipsisType
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    Final,
    Generic,
    Mapping,
    Protocol,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

from .models.exceptions import CastingError

__all__ = [
    'EnvironConfig',
    'EnvironModel',
    'EnvDef',
    'ActionInputs',
    'action_input',
    'desc',
    'EnvironmentError',
    'ValidationError',
    'CastingError',
]


T = TypeVar('T')
_MISSING = object()


@runtime_checkable
class Caster(Protocol[T]):
    """Protocol for custom caster functions."""

    def __call__(self, value: str) -> T: ...


_ENVIRON_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')
ELLIPSIS = ...


def parse_env_value(value: str | None) -> str | None:
    """Parse environment variable value, handling None and empty strings."""
    if value is None or value == '':
        return None
    return value.strip()


def get_env_key(key: str, case_sensitive: bool = False, prefix: str | None = None) -> str:
    """Get the environment variable key, optionally case-sensitive."""
    if prefix:
        key = f'{prefix}{key}'
    return key if case_sensitive else key.upper()


def load_environ_map(
    environ: Mapping[str, str | None],
    case_sensitive: bool = False,
    ignore_empty: bool = False,
) -> Mapping[str, str | None]:
    return {
        get_env_key(k, case_sensitive): parse_env_value(v)
        for k, v in environ.items()
        if not (ignore_empty and v == '')
    }


def parse_env_file(
    env_file: str | Path,
    encoding: str = 'utf-8',
    allow_empty: bool = False
) -> dict[str, str]:

    if isinstance(env_file, str):
        env_file = Path(env_file)

    if not env_file.exists():
        raise EnvironmentError(f'Environment file {env_file} does not exist.')

    contents = None
    with env_file.open(
        encoding=encoding
    ) as f:
        contents = f.read().splitlines()

    if contents is None:
        raise EnvironmentError(f'Failed to read environment file {env_file}.')

    env_vars = {}

    for lines in filter(
        lambda l: not l.startswith('#'),
        contents
    ):
        tokens = lines.replace(' ', ' ').split('=')
        if not tokens or len(tokens) < 2:
            continue

        key, value = tokens[0].lower(), tokens[1].strip('"\'')
        if not allow_empty and not value:
            continue
        env_vars[key] = value

    return env_vars


def is_required(default_value: Any | EllipsisType) -> bool:
    """Check if a default value indicates a required field."""
    return default_value is ... or default_value is EllipsisType


class EnvironConfig:
    """Configuration for environment variable loading."""

    __slots__ = (
        'prefix',
        'file',
        'encoding',
        'case_sensitive',
        'strip_values',
        'allow_empty',
        '_env_cache'
    )

    def __init__(
        self,
        prefix: str = '',
        file: str | Path | None = None,
        encoding: str = 'utf-8',
        case_sensitive: bool = False,
        strip_values: bool = True,
        allow_empty: bool = False,
    ) -> None:
        self.prefix: Final[str] = prefix
        self.file: Final[Path | None] = Path(file) if file else None
        self.encoding: Final[str] = encoding
        self.case_sensitive: Final[bool] = case_sensitive
        self.strip_values: Final[bool] = strip_values
        self.allow_empty: Final[bool] = allow_empty
        self._env_cache: dict[str, str] | None = None

    @cached_property
    def environment(self) -> dict[str, str]:
        env = dict(map(
            lambda kv: (kv[0].lower(), kv[1]),
            os.environ.items()
        ))

        if self.file and self.file.exists():
            parsed_file = parse_env_file(
                self.file,
                encoding=self.encoding,
                allow_empty=self.allow_empty,
            )
            env.update(parsed_file)

        return env

    def get_env_key(
        self,
        field_name: str,
        alias: str | None = None
    ) -> str:
        key = alias or field_name.lower()
        full_key = f'{self.prefix}{key}' if self.prefix else key
        return full_key.lower()

    def key_exists(self, env_key: str,) -> bool:
        """Check if an environment variable key exists."""
        return env_key in self.environment


class TypeCaster:
    """Handles type casting for environment variables."""

    _TRUTHISH: Final[frozenset[str]] = frozenset(
        {'true', '1', 'yes', 'on', 't', 'y'})
    _FALSY: Final[frozenset[str]] = frozenset(
        {'false', '0', 'no', 'off', 'f', 'n', ''})

    @staticmethod
    def cast_bool(value: str) -> bool:
        """Cast string to boolean."""
        lower_val = value.lower().strip()
        if lower_val in TypeCaster._TRUTHISH:
            return True
        elif lower_val in TypeCaster._FALSY:
            return False
        raise CastingError(f"Cannot cast '{value}' to bool")

    @staticmethod
    def cast_path(value: str) -> Path:
        """Cast string to Path."""
        return Path(value).expanduser().resolve()

    @staticmethod
    def cast_datetime(value: str) -> datetime:
        """Cast string to datetime using ISO format."""
        try:
            return datetime.fromisoformat(value)
        except ValueError as e:
            raise CastingError(
                f'Cannot parse datetime: {value}'
            ) from e

    @staticmethod
    def cast_list(value: str, item_type: type[T] = str) -> list[T]:
        """Cast comma-separated string to list."""
        if not value.strip():
            return []

        items = [item.strip() for item in value.split(',')]

        if item_type is str:
            return cast(list[T], items)

        caster = TypeCaster.get_caster(item_type)
        return [caster(item) for item in items]

    @staticmethod
    def cast_dict(value: str) -> dict[str, Any]:
        """Cast JSON string to dict."""
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise CastingError(
                f'Cannot parse JSON: {value}') from e

    @staticmethod
    def get_caster(type_hint: type[T]) -> Callable[[str], T]:
        """Get appropriate caster for a type hint."""
        origin = get_origin(type_hint)

        if origin is type(Union[str, None]).__class__:
            args = get_args(type_hint)
            if len(args) == 2 and type(None) in args:
                actual_type = args[0] if args[1] is type(None) else args[1]
                return TypeCaster.get_caster(actual_type)

        if origin is list:
            args = get_args(type_hint)
            item_type = args[0] if args else str
            return cast(
                Callable[[str], T],
                lambda value: TypeCaster.cast_list(value, item_type)
            )

        type_map: dict[type, Any] = {
            str: lambda v: v,
            int: lambda v: int(v),
            float: lambda v: float(v),
            bool: TypeCaster.cast_bool,
            dict: TypeCaster.cast_dict,
            Path: TypeCaster.cast_path,
            datetime: TypeCaster.cast_datetime,
        }
        return type_map.get(
            type_hint,
            lambda v: cast(T, v)  # default to identity function
        )





@dataclass
class EnvDef(Generic[T]):
    """Definition for an environment variable field."""

    default: Union[T, EllipsisType, object] = MISSING
    default_factory: Callable[[], T] | None = None
    alias: str | None = None
    caster: Caster[T] | None = None
    validator: Callable[[T], bool] | None = None
    description: str = ''

    def __post_init__(self) -> None:
        if self.default is not MISSING and self.default_factory is not None:
            raise ValueError('Cannot specify both default and default_factory')


class EnvironModelMeta(type):
    """Metaclass for EnvironModel to handle field processing."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any
    ) -> EnvironModelMeta:
        annotations: dict[str, Any] = namespace.get('__annotations__', {})

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        env_fields: dict[str, EnvDef[Any]] = {}

        for field_name, annotation in annotations.items():
            if field_name.startswith('_'):
                continue

            if hasattr(annotation, '__metadata__'):
                for metadata in annotation.__metadata__:
                    if isinstance(metadata, EnvDef):
                        env_fields[field_name] = metadata
                        break

            field_value = namespace.get(field_name, MISSING)
            if (
                isinstance(field_value, Field) and
                field_value.default_factory and
                field_value.default_factory is not MISSING
            ):
                try:
                    env_def = field_value.default_factory()
                    if isinstance(env_def, EnvDef):
                        env_fields[field_name] = env_def
                except:
                    pass

        cls._env_fields = env_fields  # type: ignore[attr-defined]
        return cls


@dataclass
class EnvironModel(metaclass=EnvironModelMeta):

    config: ClassVar[EnvironConfig]
    _env_fields: ClassVar[dict[str, EnvDef[Any]]]

    def __post_init__(self) -> None:
        """Load and validate environment variables."""
        if not hasattr(self.__class__, 'config'):
            setattr(self.__class__, 'config', EnvironConfig())

        config = self.__class__.config
        type_hints = get_type_hints(self.__class__, include_extras=True)

        for field_name, field_type in type_hints.items():
            if field_name.startswith('_') or field_name == 'config':
                continue

            env_def = self._env_fields.get(field_name)

            if hasattr(self, field_name) and getattr(self, field_name) is not MISSING:
                continue

            value = self._get_field_definition(
                field_name, field_type, env_def, config)
            setattr(self, field_name, value)

    def _resolve_env_key(
        self,
        field_name: str,
        config: EnvironConfig,
        alias: str | None = None,
    ) -> str:
        """Resolve the environment variable key for a field."""
        env_key = config.get_env_key(field_name, alias)

        raw_value = config.environment.get(env_key, _MISSING)

    def _get_field_definition(
        self,
        field_name: str,
        field_type: type[T],
        env_def: EnvDef[T] | None,
        config: EnvironConfig
    ) -> T:
        """Load a single field from environment."""
        alias = env_def.alias if env_def else None

        if raw_value is _MISSING or (not config.allow_empty and not raw_value):
            if env_def:
                if env_def.default is not MISSING and env_def.default is not ...:
                    return cast(T, env_def.default)
                elif env_def.default_factory:
                    return env_def.default_factory()
                elif env_def.default is ...:
                    raise EnvironmentError(
                        f"Required field '{field_name}' not found in environment"
                    )

            if get_origin(field_type) is Union:
                args = get_args(field_type)
                if type(None) in args:
                    return cast(T, None)

            raise ValueError(
                f"Field '{field_name}' not found in environment"
            )

        if config.strip_values and isinstance(raw_value, str):
            raw_value = raw_value.strip()

        try:
            if env_def and env_def.caster:
                value = env_def.caster(raw_value)  # type: ignore[call-arg]
            else:
                actual_type = field_type
                if hasattr(field_type, '__origin__') and field_type.__origin__ is Annotated:
                    actual_type = get_args(field_type)[0]

                caster = TypeCaster.get_caster(actual_type)
                value = caster(raw_value)  # type: ignore[call-arg]
        except Exception as e:
            raise CastingError(f"Failed to cast '{field_name}': {e}") from e

        if env_def and env_def.validator and not env_def.validator(value):
            raise ValueError(
                f"Validation failed for field '{field_name}'"
            )

        return cast(T, value)


@dataclass
class ActionInputs(EnvironModel):
    """Base class for GitHub Action inputs."""
    config = EnvironConfig(
        prefix='INPUT_',
        case_sensitive=False
    )

    def __post_init__(self) -> None:
        """Load and validate action inputs."""
        type_hints = get_type_hints(self.__class__)

        for field_name, field_type in type_hints.items():
            if field_name.startswith('_'):
                continue

            action_def = self._action_fields.get(field_name)
            if not action_def:
                continue

            if hasattr(self, field_name) and getattr(self, field_name) is not MISSING:
                continue

            value = self._load_input(field_name, field_type, action_def)
            setattr(self, field_name, value)

    def _load_input(self, field_name: str, field_type: type[T], action_def: ActionInput[T]) -> T:
        """Load a single input from environment."""


if __name__ == '__main__':
    class FooVar(EnvironModel):
        config = EnvironConfig(prefix='FOO_')

        bar: Annotated[str, EnvDef(...)]  # Required
        bar_date: Annotated[datetime, EnvDef(default=None, alias='DATE')]
        baz: Annotated[int, EnvDef(default=0)]

    # Example 2: Using desc() syntax with .env file
    class AppConfig(EnvironModel):
        config = EnvironConfig(prefix='APP_', file='.env', encoding='utf-8')

        api_key: Annotated[str,
                           EnvDef(..., description='API key for external service')]

        debug: Annotated[bool, EnvDef(
            default=False, description='Enable debug mode')]

        max_connections: Annotated[int, EnvDef(
            default=10, description='Maximum number of connections')]

    class DeployInputs(ActionInputs):
        api_url: str = action_input(
            yaml_alias='api-url',
            transformer=lambda v: v.strip().rstrip('/') if v else None,
            description='API endpoint URL',
        )

        environment: str = action_input(
            yaml_alias='environment', default='production', transformer=lambda v: v.lower().strip()
        )

        timeout: int = action_input(
            yaml_alias='timeout-seconds', default=300, transformer=lambda v: int(v))
