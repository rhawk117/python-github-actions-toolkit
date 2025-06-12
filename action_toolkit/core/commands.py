from collections.abc import Generator
import contextlib
from pathlib import Path
import sys
from typing import Literal

from .workflow_cmd.workflow import AnnotationOptions, WorkflowCommand


# Commands Documentation:
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions


def debug(message: str) -> None:
    """Invokes ::debug:: command to log a debug message,
    which is only shown if debug mode is enabled in the workflow.

    Parameters
    ----------
    message : str
        _the log message_
    """
    WorkflowCommand.emit('debug', value=message, stream=sys.stderr, debug_enabled=True)


def notice(
    message: str, *, title: str | None = None, file: str | None = None, line: int | None = None, col: int | None = None
) -> None:
    """Invokes ::notice:: command to log a notice message,
    in the action log with optional title, file, line, and
    column information.

    Parameters
    ----------
    message : str
        _the message for the warning_
    title : str | None, optional
        _the title of message_, by default None
    file : str | None, optional
        _the file to reference_, by default None
    line : int | None, optional
        _the line to reference_, by default None
    col : int | None, optional
        _col parameter_, by default None
    """

    opts = AnnotationOptions(title=title, file=file, line=line, col=col)
    WorkflowCommand.emit('notice', value=message, options=opts)


def warning(
    message: str, *, title: str | None = None, file: str | None = None, line: int | None = None, col: int | None = None
) -> None:
    """Invokes ::warning:: command to log a warning message,
    in the action log with optional title, file, line, and
    column information.

    Parameters
    ----------
    message : str
        _the message for the warning_
    title : str | None, optional
        _the title of message_, by default None
    file : str | None, optional
        _the file to reference_, by default None
    line : int | None, optional
        _the line to reference_, by default None
    col : int | None, optional
        _col parameter_, by default None
    """

    opts = AnnotationOptions(title=title, file=file, line=line, col=col)
    WorkflowCommand.emit('warning', value=message, options=opts)


def error(
    message: str, *, title: str | None = None, file: str | None = None, line: int | None = None, col: int | None = None
) -> None:
    """Invokes ::error:: command to log an error message,
    in the action log with optional title, file, line, and
    column information. This will fail the workflow run.

    Parameters
    ----------
    message : str
        _the message for the warning_
    title : str | None, optional
        _the title of message_, by default None
    file : str | None, optional
        _the file to reference_, by default None
    line : int | None, optional
        _the line to reference_, by default None
    col : int | None, optional
        _col parameter_, by default None
    """

    opts = AnnotationOptions(title=title, file=file, line=line, col=col)
    WorkflowCommand.emit('error', value=message, options=opts)


def log(
    message: str,
    level: Literal['debug', 'notice', 'warning', 'error'] = 'notice',
    *,
    title: str | None = None,
    file: str | None = None,
    line: int | None = None,
    col: int | None = None,
) -> None:
    """Log a message at the specified log level using the appropriate workflow
    command. This function abstracts the logging functionality to allowing you
    to dynamically choose the log level.

    Parameters
    ----------
    message : str
        _the message for the warning_
    title : str | None, optional
        _the title of message_, by default None
    file : str | None, optional
        _the file to reference_, by default None
    line : int | None, optional
        _the line to reference_, by default None
    col : int | None, optional
        _col parameter_, by default None
    """
    method_map = {'debug': debug, 'notice': notice, 'warning': warning, 'error': error}
    if level not in method_map:
        raise ValueError(f'Invalid log level: {level}')

    log_func = method_map[level]
    if level == 'debug':
        log_func(message)
    else:
        log_func(message, title=title, file=file, line=line, col=col)


def start_group(title: str) -> None:
    """Start a new log group with the given title, note you
    must call `end_group` to close the group or you'll get
    weird action log output.

    A log group is a way to organize related log messages and
    makes it collapsible when viewing the action logs.

    Parameters
    ----------
    title : str
        _the group title_
    """
    WorkflowCommand.emit('group', value=title)


def end_group() -> None:
    """Ends the current log group.
    This should be called after `start_group` to properly close
    the group in the action logs.

    A log group is a way to organize related log messages and
    makes it collapsible when viewing the action logs.
    """
    WorkflowCommand.emit('endgroup')


@contextlib.contextmanager
def grouped(title: str):
    """Context manager to create a log group with the given title.
    This is a convenient way to ensure that the group is properly,
    and denote a block of code that is logically grouped together

    Parameters
    ----------
    title : str
        the title for the group

    Usage:
    ---------
    ```python
    with grouped('My Group Title'):
        # Your code here
        debug('This is a debug message')
        notice('This is a notice message')
    ```

    """
    WorkflowCommand.emit('group', value=title)
    try:
        yield
    finally:
        WorkflowCommand.emit('endgroup')


def add_mask(secret: str) -> None:
    """Adds a secret to the mask list, which prevents it from being
    printed in the action logs and leaking sensitive information in
    artifacts or logs. This is useful for API keys, tokens, or any other
    secret information that should not be exposed.

    Parameters
    ----------
    secret : str
        _the secret to mask_

    Raises
    ------
    ValueError
        _if the secret is None_
    """
    if not secret:
        raise ValueError("CommandInvalid: Secrets passed to `add_mask` can't be empty.")
    WorkflowCommand.emit('add-mask', value=secret)


def set_echo(status: Literal['on', 'off']) -> None:
    """Toggles the echoing of commands in the action logs.

    Parameters
    ----------
    on : bool, optional
        _flag for echo_, by default True
    """
    if status not in ('on', 'off'):
        raise ValueError(f"Invalid status for echo: {status}. Use 'on' or 'off'.")
    WorkflowCommand.emit('echo', value=status)


def command_controls(
    token: str,
    *,
    control: Literal['stop', 'resume'],
) -> None:
    """Control the execution of commands."""
    if control not in ('stop', 'resume'):
        raise ValueError(f'Invalid command_control: {control}')
    emitted = 'stop-commands' if control == 'stop' else 'resume-commands'

    WorkflowCommand.emit(emitted, value=token)


def add_matcher(matcher_file: str | Path) -> None:
    """Add a problem matcher from a file."""
    if not matcher_file:
        raise ValueError('CommandInvalid: The matcher file provided to `add-matcher` cannot be None.')
    WorkflowCommand.emit('add-matcher', value=str(matcher_file))


def remove_matcher(owner_id: str) -> None:
    """Remove a problem matcher by its ID."""
    if not owner_id:
        raise ValueError('CommandInvalid: The owner ID provided to `remove-matcher` cannot be None.')

    WorkflowCommand.emit('remove-matcher', value='', options={'owner': owner_id})


def save_state(state_name: str, *, state_value: str | None = None) -> None:
    """Save a state variable."""
    if not state_name:
        raise ValueError('CommandInvalid: The state name provided to `save-state` cannot be empty.')

    WorkflowCommand.emit('save-state', value=state_value or '', options={'name': state_name})
