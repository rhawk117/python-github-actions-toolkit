"""
Environment Variables SDK for GitHub Actions
Provides type-safe environment variable loading with dataclass integration.
"""

from __future__ import annotations

from doctest import ELLIPSIS
import os
import json
from abc import ABC
from dataclasses import dataclass, field, fields, Field, MISSING
from datetime import datetime
from pathlib import Path
from types import EllipsisType
from typing import (
    Any, TypeVar, Generic, Callable, ClassVar,
    get_type_hints, get_origin, get_args, cast, Protocol, runtime_checkable,
    Annotated, Final, Literal, overload
)
from collections.abc import Mapping, Sequence
import inspect
from functools import cached_property
from enum import Enum
import re


__all__ = [
    'EnvironConfig',
    'EnvironModel',
    'EnvDef',
    'ActionInputs',
    'action_input',
    'desc',
    'EnvironmentError',
    'ValidationError',
    'CastingError'
]


T = TypeVar('T')
_MISSING = object()


class EnvironmentError(Exception):
    """Base exception for environment variable errors."""
    pass


class ValidationError(EnvironmentError):
    """Raised when validation fails."""
    pass


class CastingError(EnvironmentError):
    """Raised when type casting fails."""
    pass


@runtime_checkable
class Caster(Protocol[T]):
    """Protocol for custom caster functions."""
    def __call__(self, value: str) -> T: ...


class EnvironConfig:
    """Configuration for environment variable loading."""

    __slots__ = (
        'prefix', 'file', 'encoding', 'case_sensitive',
        'strip_values', 'allow_empty', '_env_cache'
    )

    def __init__(
        self,
        prefix: str = '',
        file: str | Path | None = None,
        encoding: str = 'utf-8',
        case_sensitive: bool = False,
        strip_values: bool = True,
        allow_empty: bool = False
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
        """Load and cache environment variables."""
        env = dict(os.environ)

        if self.file and self.file.exists():
            env.update(self._load_env_file())

        if not self.case_sensitive:
            env = {
                k.upper(): v for k, v in env.items()
            }

        return env

    def _load_env_file(self) -> dict[str, str]:
        """Load environment variables from a .env file."""
        if not self.file:
            return {}

        env_vars: dict[str, str] = {}
        try:
            content = self.file.read_text(encoding=self.encoding)
            for line_num, line in enumerate(content.splitlines(), 1):
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
                if not match:
                    raise EnvironmentError(
                        f"Invalid line format in {self.file}:{line_num}: {line}"
                    )

                key, value = match.groups()

                if value and value[0] in ('"', "'") and value[0] == value[-1]:
                    value = value[1:-1]

                if value and line.count('"') >= 2:
                    value = value.encode().decode('unicode_escape')

                env_vars[key] = value

        except Exception as e:
            raise EnvironmentError(f"Failed to load {self.file}: {e}") from e

        return env_vars

    def get_env_key(self, field_name: str, alias: str | None = None) -> str:
        """Get the environment variable key for a field."""
        key = alias or field_name.upper()
        full_key = f"{self.prefix}{key}" if self.prefix else key
        return full_key if self.case_sensitive else full_key.upper()


class TypeCaster:
    """Handles type casting for environment variables."""

    _TRUTHY: Final[frozenset[str]] = frozenset({'true', '1', 'yes', 'on', 't', 'y'})
    _FALSY: Final[frozenset[str]] = frozenset({'false', '0', 'no', 'off', 'f', 'n', ''})

    @staticmethod
    def cast_bool(value: str) -> bool:
        """Cast string to boolean."""
        lower_val = value.lower().strip()
        if lower_val in TypeCaster._TRUTHY:
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
            raise CastingError(f"Cannot parse datetime: {value}") from e    @staticmethod
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
            raise CastingError(f"Cannot parse JSON: {value}") from e    @classmethod
    def get_caster(cls, type_hint: type[T]) -> Callable[[str], T]:
        """Get appropriate caster for a type hint."""
        origin = get_origin(type_hint)

        # Handle Optional types (Union[T, None])
        if origin is type(Union[str, None]).__class__:
            args = get_args(type_hint)
            if len(args) == 2 and type(None) in args:
                # This is Optional[T]
                actual_type = args[0] if args[1] is type(None) else args[1]
                return cls.get_caster(actual_type)

        # Handle list types
        if origin is list:
            args = get_args(type_hint)
            item_type = args[0] if args else str
            return lambda v: cls.cast_list(v, item_type)

        # Handle dict types
        if origin is dict:
            return cls.cast_dict

        # Simple types
        if type_hint is bool:
            return cls.cast_bool
        elif type_hint is int:
            return int
        elif type_hint is float:
            return float
        elif type_hint is str:
            return str
        elif type_hint is Path:
            return cls.cast_path
        elif type_hint is datetime:
            return cls.cast_datetime

        # Default to string
        return str


ELLIPSIS = ...

@dataclass
class EnvDef(Generic[T]):
    """Definition for an environment variable field."""

    default: Union[T, EllipsisType, object] = MISSING
    default_factory: Optional[Callable[[], T]] = None
    alias: Optional[str] = None
    caster: Optional[Caster[T]] = None
    validator: Optional[Callable[[T], bool]] = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.default is not MISSING and self.default_factory is not None:
            raise ValueError("Cannot specify both default and default_factory")




class EnvironModelMeta(type):
    """Metaclass for EnvironModel to handle field processing."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any
    ) -> EnvironModelMeta:
        # Process annotations
        annotations = namespace.get('__annotations__', {})

        # Create the class first
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Process environment fields
        env_fields: dict[str, EnvDef[Any]] = {}

        for field_name, annotation in annotations.items():
            if field_name.startswith('_'):
                continue

            # Check if it's an Annotated type with EnvDef
            if hasattr(annotation, '__metadata__'):
                for metadata in annotation.__metadata__:
                    if isinstance(metadata, EnvDef):
                        env_fields[field_name] = metadata
                        break

            # Check for desc() usage
            field_value = namespace.get(field_name, MISSING)
            if isinstance(field_value, Field):
                if field_value.default_factory:
                    try:
                        env_def = field_value.default_factory()
                        if isinstance(env_def, EnvDef):
                            env_fields[field_name] = env_def
                    except:
                        pass

        # Store processed fields
        cls._env_fields = env_fields  # type: ignore[attr-defined]

        return cls


@dataclass
class EnvironModel(metaclass=EnvironModelMeta):
    """Base class for environment variable models."""

    config: ClassVar[EnvironConfig]
    _env_fields: ClassVar[dict[str, EnvDef[Any]]]

    def __post_init__(self) -> None:
        """Load and validate environment variables."""
        if not hasattr(self.__class__, 'config'):
            raise TypeError(f"{self.__class__.__name__} must define 'config' class variable")

        config = self.__class__.config
        type_hints = get_type_hints(self.__class__, include_extras=True)

        for field_name, field_type in type_hints.items():
            if field_name.startswith('_') or field_name == 'config':
                continue

            # Get EnvDef if available
            env_def = self._env_fields.get(field_name)

            # Skip if already has a value
            if hasattr(self, field_name) and getattr(self, field_name) is not MISSING:
                continue

            # Load from environment
            value = self._load_field(field_name, field_type, env_def, config)
            setattr(self, field_name, value)

    def _load_field(
        self,
        field_name: str,
        field_type: Type[T],
        env_def: Optional[EnvDef[T]],
        config: EnvironConfig
    ) -> T:
        """Load a single field from environment."""
        # Get environment key
        alias = env_def.alias if env_def else None
        env_key = config.get_env_key(field_name, alias)

        # Get raw value
        raw_value = config.environment.get(env_key, _MISSING)

        # Handle missing values
        if raw_value is _MISSING or (not config.allow_empty and not raw_value):
            if env_def:
                if env_def.default is not MISSING and env_def.default is not ...:
                    return cast(T, env_def.default)
                elif env_def.default_factory:
                    return env_def.default_factory()
                elif env_def.default is ...:
                    raise ValidationError(f"Required field '{field_name}' not found in environment")

            # Check for Optional types
            if get_origin(field_type) is Union:
                args = get_args(field_type)
                if type(None) in args:
                    return cast(T, None)

            raise ValidationError(f"Field '{field_name}' not found in environment")

        # Strip value if configured
        if config.strip_values and isinstance(raw_value, str):
            raw_value = raw_value.strip()

        # Cast value
        try:
            if env_def and env_def.caster:
                value = env_def.caster(raw_value)
            else:
                # Extract actual type from Annotated
                actual_type = field_type
                if hasattr(field_type, '__origin__') and field_type.__origin__ is Annotated:
                    actual_type = get_args(field_type)[0]

                caster = TypeCaster.get_caster(actual_type)
                value = caster(raw_value)
        except Exception as e:
            raise CastingError(f"Failed to cast '{field_name}': {e}") from e

        # Validate if validator provided
        if env_def and env_def.validator:
            if not env_def.validator(value):
                raise ValidationError(f"Validation failed for field '{field_name}'")

        return cast(T, value)


@dataclass
class ActionInput(Generic[T]):
    """Definition for a GitHub Action input."""

    yaml_alias: str
    default: Union[T, object] = MISSING
    transformer: Optional[Callable[[str], T]] = None
    required: bool = True
    description: str = ""


def action_input(
    yaml_alias: str,
    *,
    default: Union[T, object] = MISSING,
    transformer: Optional[Callable[[str], T]] = None,
    required: bool = True,
    description: str = ""
) -> Any:
    """Create an ActionInput field descriptor."""
    return field(default_factory=lambda: ActionInput(
        yaml_alias=yaml_alias,
        default=default,
        transformer=transformer,
        required=required,
        description=description
    ))


class ActionInputsMeta(type):
    """Metaclass for ActionInputs to handle input processing."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any
    ) -> ActionInputsMeta:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Process action inputs
        action_fields: dict[str, ActionInput[Any]] = {}

        for field_name, field_value in namespace.items():
            if isinstance(field_value, Field) and field_value.default_factory:
                try:
                    input_def = field_value.default_factory()
                    if isinstance(input_def, ActionInput):
                        action_fields[field_name] = input_def
                except:
                    pass

        cls._action_fields = action_fields  # type: ignore[attr-defined]

        return cls


@dataclass
class ActionInputs(metaclass=ActionInputsMeta):
    """Base class for GitHub Action inputs."""

    _action_fields: ClassVar[dict[str, ActionInput[Any]]]

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

    def _load_input(
        self,
        field_name: str,
        field_type: Type[T],
        action_def: ActionInput[T]
    ) -> T:
        """Load a single input from environment."""
        # GitHub Actions converts input names to uppercase with INPUT_ prefix
        env_key = f"INPUT_{action_def.yaml_alias.upper().replace('-', '_')}"

        raw_value = os.environ.get(env_key, _MISSING)

        if raw_value is _MISSING:
            if action_def.default is not MISSING:
                return cast(T, action_def.default)
            elif not action_def.required:
                if get_origin(field_type) is Union:
                    args = get_args(field_type)
                    if type(None) in args:
                        return cast(T, None)
            else:
                raise ValidationError(f"Required input '{field_name}' not found")

        # Transform value
        try:
            if action_def.transformer:
                value = action_def.transformer(raw_value)
            else:
                # Use TypeCaster for standard types
                caster = TypeCaster.get_caster(field_type)
                value = caster(raw_value)
        except Exception as e:
            raise CastingError(f"Failed to transform input '{field_name}': {e}") from e

        return cast(T, value)


# Example usage demonstrating the implementation
if __name__ == "__main__":
    # Example 1: Basic environment model
    class FooVar(EnvironModel):
        config = EnvironConfig(prefix='FOO_')

        bar: Annotated[str, EnvDef(...)]  # Required
        bar_date: Annotated[datetime, EnvDef(
            default=None,
            alias='DATE'
        )]
        baz: Annotated[int, EnvDef(default=0)]

    # Example 2: Using desc() syntax with .env file
    class AppConfig(EnvironModel):
        config = EnvironConfig(
            prefix='APP_',
            file='.env',
            encoding='utf-8'
        )

        api_key: Annotated[str, EnvDef(
            ...,
            description="API key for external service"
        )]

        debug: Annotated[bool, EnvDef(
            default=False,
            description="Enable debug mode"
        )]

        max_connections: Annotated[int, EnvDef(
            default=10,
            description="Maximum number of connections"
        )]

    class DeployInputs(ActionInputs):
        api_url: str = action_input(
            yaml_alias='api-url',
            transformer=lambda v: v.strip().rstrip('/') if v else None,
            description="API endpoint URL"
        )

        environment: str = action_input(
            yaml_alias='environment',
            default='production',
            transformer=lambda v: v.lower().strip()
        )

        timeout: int = action_input(
            yaml_alias='timeout-seconds',
            default=300,
            transformer=lambda v: int(v)
        )