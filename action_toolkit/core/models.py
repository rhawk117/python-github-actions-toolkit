

from ast import Not
from enum import StrEnum
from typing import NotRequired, TypeAlias

import dataclasses
from .exceptions import AnnotationError

CommandPropertyValue: TypeAlias = str | int | float | bool | None
CommandValue: TypeAlias = str | int | float | bool | list | dict | None




class GithubCommand(StrEnum):
    """
    GitHub Actions workflow commands.

    These commands are interpreted by the GitHub Actions runner
    when formatted as ::command::message
    """

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
    ADD_MASK = 'add-mask'  # for secrets
    ECHO = 'echo'
    FILE_COMMAND = 'file-command'  # for file commands (newer style)


@dataclasses.dataclass(frozen=True, slots=True)
class AnnotationProperties:
    """
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
    """

    title: str | None = None
    file: str | None = None
    startLine: int | None = None
    endLine: int | None = None
    startColumn: int | None = None
    endColumn: int | None = None

    def __post_init__(self) -> None:
        """Validate annotation properties constraints."""
        if self.startColumn is not None or self.endColumn is not None:
            if self.startLine != self.endLine and self.endLine is not None:
                raise AnnotationError(
                    'startColumn and endColumn cannot be sent when startLine and endLine are different values'
                )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Command:
    '''
    Represents an emittable Github Actions command.
    '''
    command: GithubCommand
    properties: dict[str, CommandPropertyValue] = dataclasses.field(default_factory=dict)
    message: CommandValue