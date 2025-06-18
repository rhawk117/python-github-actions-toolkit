'''
**core.internals.types** module
Type definitions and constants for GitHub Actions toolkit.

This module provides type definitions, enums, and constants that mirror
the TypeScript types in @actions/core and are provided for code readability
and convience
'''

from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from .exceptions import AnnotationError






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



class LogLevel(StrEnum):
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
    start_line : Optional[int]
        The start line for the annotation.
    end_line : Optional[int]
        The end line for the annotation. Defaults to start_line when
        start_line is provided.
    start_col : Optional[int]
        The start column for the annotation. Cannot be sent when
        start_line and end_line are different values.
    end_col : Optional[int]
        The end column for the annotation. Cannot be sent when
        start_line and end_line are different values. Defaults to
        start_col when start_col is provided.
    '''
    title: str | None = None
    file: str | None = None
    start_line: int | None = None # startLine
    end_line: int | None = None # endLine
    start_col: int | None = None # startColumn
    end_col: int | None = None # endColumn

    def __post_init__(self) -> None:
        '''Validate annotation properties constraints.'''
        if self.start_col is not None or self.end_col is not None:
            if self.start_line != self.end_line and self.end_line is not None:
                raise AnnotationError(
                    'start_col and end_col cannot be sent when '
                    'start_line and end_line are different values'
                )

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
