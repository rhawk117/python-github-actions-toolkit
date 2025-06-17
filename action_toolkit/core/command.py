"""
**core.command**
API for using commands for GitHub Actions

Learn more
----------
https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions

"""

from __future__ import annotations
from logging import warn
import os
import sys
import warnings
from contextlib import contextmanager

from typing import TYPE_CHECKING
from .internals import commands
from .internals.interfaces import (
    ExitCode,
    AnnotationProperties,
    WorkflowCommand,
    WorkflowEnv
)

if TYPE_CHECKING:
    from action_toolkit.corelib.types.core import StringOrException
    from action_toolkit.corelib.types.io import IOValue, StringOrPathlib


def set_output(*, name: str, value: IOValue) -> None:
    """
    Set the value of an output.

    This function mirrors setOutput in core.ts. Output values can
    be used by subsequent steps in the workflow.

    Parameters
    ----------
    name : str
        Name of the output to set.
    value : IOValue
        Value to store. Non-string values will be JSON stringified.

    Notes
    -----
    The function uses the newer file-based approach (GITHUB_OUTPUT)
    when available, falling back to set-output command for compatibility.

    Examples
    --------
    >>> set_output(name='result', value='success')
    >>> set_output(name='count', value=42)
    >>> set_output(name='data', value={'key': 'value'})
    """
    output_file = os.environ.get(WorkflowEnv.GITHUB_OUTPUT, None)
    if output_file:
        commands.issue_file_command(
            "OUTPUT",
            commands.prepare_key_value_message(name, value),
            file_path=output_file
        )
    else:
        warnings.warn(
            "Could not find GITHUB_OUTPUT environment variable, "
            "and had to use set-output command instead. This approach is deprecated and "
            "could not longer be functioning.",
            category=RuntimeWarning,
            stacklevel=2
        )
        commands.issue_command(
            command=WorkflowCommand.SET_OUTPUT,
            properties={"name": name},
            message=value
        )


def set_command_echo(*, enabled: bool) -> None:
    """
    Enable or disable echoing of workflow commands.

    This function mirrors setCommandEcho in core.ts. When enabled,
    workflow commands are echoed to the log.

    Parameters
    ----------
    enabled : bool
        Whether to echo commands.

    Examples
    --------
    >>> # Enable command echoing for debugging
    >>> set_command_echo(enabled=True)

    >>> # Disable command echoing (default)
    >>> set_command_echo(enabled=False)
    """
    commands.issue(name=WorkflowCommand.ECHO, message="on" if enabled else "off")

def set_failed(*, message: str | Exception) -> None:
    """
    Set the action status to failed and exit.

    This function mirrors setFailed in core.ts. It logs an error
    message and exits with a failure code.

    Parameters
    ----------
    message : Union[str, Exception]
        Error message or exception.

    Notes
    -----
    This function does not return - it exits the process with code 1.

    Examples
    --------
    >>> try:
    ...     # Some operation
    ...     result = risky_operation()
    ... except Exception as e:
    ...     set_failed(message=e)
    """
    error(message=str(message))
    sys.exit(ExitCode.Failure)


def is_debug() -> bool:
    """
    Check if runner is in debug mode.

    This function mirrors isDebug in core.ts. Debug mode can be
    enabled by setting the RUNNER_DEBUG secret to '1'.

    Returns
    -------
    bool
        True if runner is in debug mode, False otherwise.

    Examples
    --------
    >>> if is_debug():
    ...     debug(message='Detailed debug information...')
    """
    return os.environ.get(WorkflowEnv.RUNNER_DEBUG, "0") == "1"


def export_variable(*, name: str, value: IOValue) -> None:
    """
    Sets an environment variable for this action and future actions in the job.

    Similar exportVariable in core.ts. It sets the variable
    in the current process and also exports it for subsequent actions.

    Parameters
    ----------
    name : str
        The name of the variable to set.
    value : IOValue
        The value of the variable. Will be converted to string.

    Notes
    -----
    The function uses the newer file-based approach (GITHUB_ENV) when
    available, falling back to the set-env command for compatibility.

    Examples
    --------
    >>> export_variable(name='MY_VAR', value='my value')
    >>> export_variable(name='BUILD_NUMBER', value=42)
    """
    str_value = str(value)

    os.environ[name] = str_value

    env_file = os.environ.get(WorkflowEnv.GITHUB_ENV, None)
    if env_file:
        commands.issue_file_command(
            "ENV",
            commands.prepare_key_value_message(name, value),
            file_path=env_file,
        )
    else:
        warnings.warn(
            "Could not find GITHUB_ENV environment variable,  "
            "using set-env command instead. This approach is depracated and "
            "may not work in all environments.",
            category=RuntimeWarning,
            stacklevel=2
        )
        commands.issue_command(
            command=WorkflowCommand.SET_ENV,
            properties={"name": name},
            message=value
        )

def set_secret(*, secret: str | IOValue) -> None:
    """
    Register a secret which will get masked from logs, equivalent to add-mask
    command.

    This function mirrors setSecret in core.ts. Any future occurrence
    of the secret value in logs will be replaced with ***.

    Parameters
    ----------
    secret : Union[str, IOValue]
        Value to be masked in logs. Will be converted to string.

    Examples
    --------
    >>> set_secret(secret='my-password-123')
    >>> set_secret(secret={'apiKey': 'secret-key'})  # JSON serialized
    """
    try:
        commands.issue_command(
            command=WorkflowCommand.ADD_MASK,
            properties={},
            message=secret
        )
    except Exception as e:
        warnings.warn(
            f"!!! WARNING !!! Could not set secret with add-mask command: {e}. "
            "This may be due to the command not being supported in this environment. ",
            category=RuntimeWarning,
            stacklevel=2,
        )


def add_path(*, path: StringOrPathlib) -> None:
    """
    Prepend a directory to the system PATH.

    This function mirrors addPath in core.ts. The path is added
    to the current process and exported for subsequent actions.

    Parameters
    ----------
    path : Union[str, Path]
        Directory to add to PATH.

    Examples
    --------
    >>> add_path(path='/usr/local/bin')
    >>> add_path(path=Path.home() / '.local' / 'bin')
    """
    path_str = str(path)

    current_path = os.environ.get("PATH", "")
    if not current_path:
        warnings.warn(
            "The PATH environment variable is not set. "
            "This may cause issues with finding executables.",
            category=RuntimeWarning,
            stacklevel=2,
        )

    os.environ["PATH"] = f"{path_str}{os.pathsep}{current_path}"

    path_file = os.environ.get(WorkflowEnv.GITHUB_PATH, None)
    if path_file:
        with open(path_file, "a", encoding="utf-8") as f:
            f.write(path_str + os.linesep)
    else:
        commands.issue_command(
            command=WorkflowCommand.ADD_PATH,
            properties={},
            message=path_str
        )


def get_state(*, name: str) -> str:
    """
    Get the value of a saved state.

    This function mirrors getState in core.ts. Retrieves state
    that was previously saved with save_state.

    Parameters
    ----------
    name : str
        Name of the state to retrieve.

    Returns
    -------
    str
        The state value, or empty string if not found.

    Examples
    --------
    >>> # Retrieve previously saved state
    >>> temp_dir = get_state(name='temp_dir')
    >>> if temp_dir:
    ...     cleanup_temp_dir(temp_dir)
    """
    return os.environ.get(f"STATE_{name}", "")


def save_state(*, name: str, value: IOValue) -> None:
    """
    Save state for sharing between pre/main/post actions.

    This function mirrors saveState in core.ts. State can be
    retrieved in subsequent action phases using get_state.

    Parameters
    ----------
    name : str
        Name of the state to store.
    value : IOValue
        Value to store. Non-string values will be JSON stringified.

    Notes
    -----
    State is only available within the same action execution.
    It cannot be accessed by other actions or steps.

    Examples
    --------
    >>> # In main action
    >>> save_state(name='temp_dir', value='/tmp/build-123')

    >>> # In post action
    >>> temp_dir = get_state(name='temp_dir')
    """
    state_file = os.environ.get(WorkflowEnv.GITHUB_STATE, None)
    if state_file:
        commands.issue_file_command(
            "STATE",
            commands.prepare_key_value_message(name, value),
            file_path=state_file,
        )
    else:
        commands.issue_command(
            command=WorkflowCommand.SAVE_STATE,
            properties={"name": name},
            message=value,
        )

def debug(*, message: str) -> None:
    """
    Write debug message to log.

    This function mirrors debug in core.ts. Debug messages are
    hidden by default unless debug mode is enabled.

    Parameters
    ----------
    message : str
        Debug message.

    Examples
    --------
    >>> debug(message='Entering function X with params Y')
    """
    commands.issue_command(
        command=WorkflowCommand.DEBUG,
        properties={},
        message=message
    )

def notice(message: str, *, properties: AnnotationProperties | None = None) -> None:
    """
    Write a notice message to log.

    This function mirrors notice in core.ts. Notices create
    annotations that are shown prominently in the UI.

    Parameters
    ----------
    message : str
        Notice message.
    properties : Optional[AnnotationProperties]
        Properties to control annotation appearance and location.

    Examples
    --------
    >>> notice(message='Deployment completed successfully')

    >>> notice(
    ...     message='Configuration updated',
    ...     properties=AnnotationProperties(
    ...         title='Config Change',
    ...         file='config.yaml',
    ...         startLine=10
    ...     )
    ... )
    """
    cmd_properties = commands.to_command_properties(
        annotation_properties=properties or AnnotationProperties()
    )
    commands.issue_command(
        command=WorkflowCommand.NOTICE,
        properties=cmd_properties,
        message=message
    )

def warning(
    message: StringOrException,
    *,
    properties: AnnotationProperties | None = None
) -> None:
    """
    Write a warning message to log.

    This function mirrors warning in core.ts. Warnings create
    yellow annotations in the workflow summary.

    Parameters
    ----------
    message : Union[str, Exception]
        Warning message or exception.
    properties : Optional[AnnotationProperties]
        Properties to control annotation appearance and location.

    Examples
    --------
    >>> warning(message='Deprecated function used')

    >>> warning(
    ...     message='Low disk space',
    ...     properties=AnnotationProperties(
    ...         title='Resource Warning',
    ...         file='disk_check.py',
    ...         startLine=45
    ...     )
    ... )
    """
    cmd_properties = commands.to_command_properties(
        annotation_properties=properties or AnnotationProperties()
    )
    commands.issue_command(
        command=WorkflowCommand.WARNING,
        properties=cmd_properties,
        message=str(message)
    )


def error(
    message: StringOrException,
    *,
    properties: AnnotationProperties | None = None
) -> None:
    """
    Write an error message to log.

    This function mirrors error in core.ts. Errors create red
    annotations in the workflow summary.

    Parameters
    ----------
    message : Union[str, Exception]
        Error message or exception.
    properties : Optional[AnnotationProperties]
        Properties to control annotation appearance and location.

    Examples
    --------
    >>> error(message='File not found: data.csv')

    >>> try:
    ...     process_file()
    ... except Exception as e:
    ...     error(
    ...         message=e,
    ...         properties=AnnotationProperties(
    ...             title='Processing Error',
    ...             file='processor.py',
    ...             startLine=102
    ...         )
    ...     )
    """
    cmd_properties = commands.to_command_properties(
        annotation_properties=properties or AnnotationProperties()
    )
    commands.issue_command(
        command=WorkflowCommand.ERROR,
        properties=cmd_properties,
        message=str(message)
    )

def start_group(*, name: str) -> None:
    """
    Begin an output group.

    This function mirrors startGroup in core.ts. Output groups
    create collapsible sections in the workflow logs.

    Parameters
    ----------
    name : str
        Name of the output group.

    See Also
    --------
    end_group : End an output group
    group : Context manager for groups

    Examples
    --------
    >>> start_group(name='Build Dependencies')
    >>> # ... build output ...
    >>> end_group()
    """
    commands.issue(name=WorkflowCommand.GROUP, message=name)

def end_group() -> None:
    """
    End an output group.

    This function mirrors endGroup in core.ts. Must be called
    after start_group to close the collapsible section.

    See Also
    --------
    start_group : Begin an output group
    group : Context manager for groups

    Examples
    --------
    >>> start_group(name='Test Results')
    >>> # ... test output ...
    >>> end_group()
    """
    commands.issue(name=WorkflowCommand.ENDGROUP)

@contextmanager
def group(*, name: str):
    """
    Context manager for output groups.

    This provides a Pythonic interface for creating collapsible
    log sections, ensuring groups are properly closed.

    Parameters
    ----------
    name : str
        Name of the output group.

    Yields
    ------
    None

    Examples
    --------
    >>> with group(name='Setup Environment'):
    ...     info(message='Installing dependencies...')
    ...     # ... setup code ...
    ...     info(message='Environment ready')
    """
    start_group(name=name)
    try:
        yield
    finally:
        end_group()
