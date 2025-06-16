'''
Type definitions and constants for GitHub Actions toolkit.

This module provides type definitions, enums, and constants that mirror
the TypeScript types in @actions/core.
'''

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from pathlib import Path

try:
    from typing import TypeAlias  # Python 3.11+
except ImportError:
    from typing_extensions import TypeAlias  # Python 3.8-3.10

from .exceptions import AnnotationError


CommandValue: TypeAlias = str | int | float | bool | list | dict | None
CommandPropertyValue: TypeAlias = str | int | float | bool | None


class ExitCode(IntEnum):
    '''
    Standard exit codes.

    Mirrors the exit codes used in the TypeScript toolkit where
    0 indicates success and 1 indicates failure, little verbose
    but mirrors original sdk.
    '''
    Success = 0
    Failure = 1


class WorkflowCommand(StrEnum):
    '''
    GitHub Actions workflow commands.

    These commands are interpreted by the GitHub Actions runner
    when formatted as ::command::message
    '''
    # output commands
    SET_OUTPUT = 'set-output'
    SET_ENV = 'set-env'
    ADD_PATH = 'add-path'

    # logging commands
    DEBUG = 'debug'
    NOTICE = 'notice'
    WARNING = 'warning'
    ERROR = 'error'

    GROUP = 'group'
    ENDGROUP = 'endgroup'

    SAVE_STATE = 'save-state'
    ADD_MASK = 'add-mask' # for secrets
    ECHO = 'echo'
    FILE_COMMAND = 'file-command' # for file commands (newer style)



class LogLevel(str, Enum):
    '''
    Log levels for GitHub Actions.

    Corresponds to the different annotation levels available
    in the GitHub Actions workflow commands.
    '''
    DEBUG = 'debug'
    INFO = 'info'
    NOTICE = 'notice'
    WARNING = 'warning'
    ERROR = 'error'


@dataclass(frozen=True, slots=True)
class AnnotationProperties:
    '''
    Properties for workflow command annotations.

    Mirrors TypeScript's AnnotationProperties interface. These properties
    allow annotations to be attached to specific locations in source files.

    Attributes
    ----------
    title : Optional[str]
        A title for the annotation.
    file : Optional[str]
        The name of the file for which the annotation should be created.
    startLine : Optional[int]
        The start line for the annotation.
    endLine : Optional[int]
        The end line for the annotation. Defaults to startLine when
        startLine is provided.
    startColumn : Optional[int]
        The start column for the annotation. Cannot be sent when
        startLine and endLine are different values.
    endColumn : Optional[int]
        The end column for the annotation. Cannot be sent when
        startLine and endLine are different values. Defaults to
        startColumn when startColumn is provided.
    '''
    title: str | None = None
    file: str | None = None
    startLine: int | None = None
    endLine: int | None = None
    startColumn: int | None = None
    endColumn: int | None = None

    def __post_init__(self) -> None:
        '''Validate annotation properties constraints.'''
        if self.startColumn is not None or self.endColumn is not None:
            if self.startLine != self.endLine and self.endLine is not None:
                raise AnnotationError(
                    'startColumn and endColumn cannot be sent when '
                    'startLine and endLine are different values'
                )


@dataclass(slots=True)
class InputOptions:
    '''
    Options for getting action inputs.

    Mirrors TypeScript's InputOptions interface.

    Attributes
    ----------
    required : bool
        Whether the input is required. If true and the input is not
        provided, a ValueError will be raised. Default is False.
    trimWhitespace : bool
        Whether to trim whitespace from the input value. Default is True.
    '''
    required: bool = False
    trimWhitespace: bool = True


@dataclass(slots=True)
class MultilineInputOptions(InputOptions):
    '''
    Options for getting multiline action inputs.

    Extends InputOptions with multiline-specific behavior.

    Attributes
    ----------
    skipEmptyLines : bool
        Whether to filter out empty lines. Default is True.
    '''
    skipEmptyLines: bool = True


class WorkflowEnv(StrEnum):
    '''
    Environment variables used in GitHub Actions workflows.

    These are the environment variables that are set by the GitHub Actions
    runner and can be used within actions.
    '''
    GITHUB_OUTPUT = 'GITHUB_OUTPUT'
    GITHUB_STATE = 'GITHUB_STATE'
    GITHUB_PATH = 'GITHUB_PATH'
    GITHUB_ENV = 'GITHUB_ENV'
    RUNNER_DEBUG = 'RUNNER_DEBUG'
    GITHUB_WORKSPACE = 'GITHUB_WORKSPACE'
    GITHUB_ACTION = 'GITHUB_ACTION'
    GITHUB_ACTION_PATH = 'GITHUB_ACTION_PATH'


# YAML 1.2 boolean values (case-insensitive)
YAML_BOOLEAN_TRUE = frozenset(['true', 'yes', 'on', 'y', '1'])
YAML_BOOLEAN_FALSE = frozenset(['false', 'no', 'off', 'n', '0'])

IOValue: TypeAlias = str | int | float | bool
StringOrPath: TypeAlias = str | Path
StringOrException: TypeAlias = str | Exception
