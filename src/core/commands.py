
from collections.abc import Generator
import contextlib
from pathlib import Path
import sys
from typing import Literal

from .workflow_cmd.workflow import AnnotationOptions, WorkflowCommand

LogLevel = Literal['debug', 'notice', 'warning', 'error']

# Commands Documentation:
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions

def debug(message: str) -> None:
    """Log a debug message."""
    WorkflowCommand.emit(
        'debug',
        value=message,
        stream=sys.stderr,
        debug_enabled=True
    )

def notice(
    message: str,
    *,
    title: str | None = None,
    file: str | None = None,
    line: int | None = None,
    col: int | None = None
) -> None:
    """Log a notice message."""

    opts = AnnotationOptions(
        title=title,
        file=file,
        line=line,
        col=col
    )
    WorkflowCommand.emit(
        'notice',
        value=message,
        options=opts
    )

def warning(
    message: str,
    *,
    title: str | None = None,
    file: str | None = None,
    line: int | None = None,
    col: int | None = None
) -> None:
    """Log a warning message."""

    opts = AnnotationOptions(
        title=title,
        file=file,
        line=line,
        col=col
    )
    WorkflowCommand.emit(
        'warning',
        value=message,
        options=opts
    )

def error(
    message: str,
    *,
    title: str | None = None,
    file: str | None = None,
    line: int | None = None,
    col: int | None = None
) -> None:
    """Log an error message."""

    opts = AnnotationOptions(
        title=title,
        file=file,
        line=line,
        col=col
    )
    WorkflowCommand.emit(
        'error',
        value=message,
        options=opts
    )


def log(
    message: str,
    level: LogLevel = 'notice',
    *,
    title: str | None = None,
    file: str | None = None,
    line: int | None = None,
    col: int | None = None
) -> None:
    method_map = {
        'debug': debug,
        'notice': notice,
        'warning': warning,
        'error': error
    }
    if level not in method_map:
        raise ValueError(f"Invalid log level: {level}")

    log_func = method_map[level]
    if level == 'debug':
        log_func(message)
    else:
        log_func(
            message,
            title=title,
            file=file,
            line=line,
            col=col
        )


def start_group(title: str) -> None:
    """Start a log group."""
    WorkflowCommand.emit('group', value=title)

def end_group() -> None:
    """End the current log group."""
    WorkflowCommand.emit('endgroup')

@contextlib.contextmanager
def grouped(title: str):
    """Context manager for grouping logs."""
    WorkflowCommand.emit('group', value=title)
    try:
        yield
    finally:
        WorkflowCommand.emit('endgroup')

def add_mask(secret: str) -> None:
    """Add a secret to the mask list."""
    if not secret:
        raise ValueError('CommandInvalid: Secrets passed to `add_mask` can\'t be empty.')
    WorkflowCommand.emit('add-mask', value=secret)

def echo(on: bool = True) -> None:
    """Control the visibility of command output."""
    WorkflowCommand.emit('echo', value='on' if on else 'off')

def command_controls(
    token: str,
    *,
    control: Literal['stop', 'resume'],
) -> None:
    """Control the execution of commands."""
    if control not in ['stop', 'resume']:
        raise ValueError(f"Invalid control: {control}")
    emitted = 'stop-commands' if control == 'stop' else 'resume-commands'

    WorkflowCommand.emit(emitted, value=token)

def add_matcher(matcher_file: str | Path) -> None:
    """Add a problem matcher from a file."""
    if not matcher_file:
        raise ValueError('CommandInvalid: The matcher file provided to `add-matcher` cannot be empty.')
    WorkflowCommand.emit('add-matcher', value=str(matcher_file))

def remove_matcher(owner_id: str) -> None:
    """Remove a problem matcher by its ID."""
    if not owner_id :
        raise ValueError('CommandInvalid: The owner ID provided to `remove-matcher` cannot be empty.')
    WorkflowCommand.emit(
        'remove-matcher',
        value='',
        options={'owner': owner_id}
    )

def save_state(
    state_name: str,
    *,
    state_value: str | None = None
) -> None:
    """Save a state variable."""
    if not state_name:
        raise ValueError('CommandInvalid: The state name provided to `save-state` cannot be empty.')
    WorkflowCommand.emit(
        'save-state',
        value=state_value or '',
        options={'name': state_name}
    )

