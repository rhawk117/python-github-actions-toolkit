"""
**core.command**
API for using commands for GitHub Actions

Learn more
----------
https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions

"""

from __future__ import annotations

import os
from pathlib import Path
import sys

from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal

from . import utils
from .models import (
    GithubCommand,
    CommandPropertyValue,
    CommandValue,
    Command,
    AnnotationProperties
)

if TYPE_CHECKING:
    from action_toolkit.corelib.types.core import StringOrException
    from action_toolkit.corelib.types.io import IOValue, StringOrPathlib


BOOLEAN_TRUE = frozenset(['true', 'yes', 'on', 'y', '1'])
BOOLEAN_FALSE = frozenset(['false', 'no', 'off', 'n', '0'])


def emit_command(
    name: GithubCommand,
    properties: dict[str, CommandPropertyValue] | None | str = None,
    *,
    message: CommandValue
) -> None:

    properties = properties or {}

    cmd = Command(
        command=name,
        properties=properties,  # type: ignore[assignment]
        message=message
    )

    emittable_string = utils.get_command_string(cmd)
    sys.stdout.write(f'{emittable_string}{os.linesep}')
    sys.stdout.flush()


def emit(name: GithubCommand, message: CommandValue = '') -> None:
    """
    Emit a command to the GitHub Actions runner.

    This function mirrors issue in core.ts. It formats the command
    and writes it to standard output, which the runner interprets.

    Parameters
    ----------
    name : GithubCommand
        The command to issue.
    message : CommandValue, optional
        The message to include with the command. Defaults to an empty string.

    Examples
    --------
    >>> emit(name=GithubCommand.DEBUG, message='Debugging information')
    >>> emit(name=GithubCommand.ERROR, message='An error occurred')
    """
    emit_command(name=name, message=message)


def emit_file_command(name: Literal['ENV', 'OUTPUT', 'STATE'], message: CommandValue) -> None:
    environ_key = f'GITHUB_{name.upper()}'
    path_str = os.getenv(environ_key)
    if not path_str:
        raise RuntimeError(
            f'The ::{name.lower()}:: command requires the {environ_key} environment variable and is deprecated.'
            ' The environment variable is not set or does not exist.'
        )
    file_path = Path(path_str).expanduser().resolve()
    cmd_str = f'{utils.to_command_value(message)}{os.linesep}'
    with file_path.open('a', encoding='utf-8') as f:
        f.write(cmd_str)


def environ_contains(name: str) -> bool:
    """
    Check if the environment variable exists.

    This function checks if a specific environment variable is set.
    It is used to determine if the newer file-based approach (GITHUB_ENV, GITHUB_OUTPUT)
    is available.

    Parameters
    ----------
    name : str
        Name of the environment variable to check.

    Returns
    -------
    bool
        True if the environment variable exists, False otherwise.
    """
    return name in os.environ


def export_variable(name: str, value: IOValue) -> None:
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
    var_value = utils.to_command_value(value)
    os.environ[name] = var_value

    if environ_contains('GITHUB_ENV'):
        return emit_file_command(
            'ENV',
            utils.prepare_key_value_message(name, var_value),
        )

    emit_command(
        GithubCommand.SET_ENV,
        {'name': name},
        message=var_value
    )


def set_secret(secret: str) -> None:
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
        emit_command(
            GithubCommand.ADD_MASK,
            message=secret
        )
    except Exception as e:
        raise RuntimeError(
            'Could not set secret. This may be due to an invalid value or an issue with the environment.'
            'For security reasons, the program will now exit.'
        ) from e


def add_path(path: StringOrPathlib) -> None:
    if environ_contains('GITHUB_PATH'):
        emit_file_command('ENV', str(path))
    else:
        emit_command(GithubCommand.ADD_PATH, message=str(path))

    appended_paths = f'{path}{os.pathsep}{os.getenv('PATH', '')}'
    os.environ['PATH'] = appended_paths


def get_input(
    name: str,
    *,
    required: bool = False,
    trim_whitespace: bool = True
) -> str:

    input_environ = f'INPUT_{name.upper()}'.replace('-', '_').upper()

    input = os.environ.get(input_environ, '')

    if not input and required:
        raise ValueError(
            f'Input required and not supplied: {name}'
        )

    if not trim_whitespace:
        return input

    return input.strip()


def get_multiline_input(
    name: str,
    *,
    required: bool = False,
    trim_whitespace: bool = True
) -> list[str]:
    inputs = get_input(
        name,
        required=required,
        trim_whitespace=trim_whitespace
    )
    input_lines = filter(
        lambda x: x.strip() != '',
        inputs.split('\n')
    )

    return [input_lines.strip() for input_lines in input_lines]


def get_boolean_input(
    name: str,
    *,
    required: bool = False,
    trim_whitespace: bool = True
) -> bool:
    """
    Get a boolean input value from the environment.

    This function retrieves an input value and converts it to a boolean.
    It supports 'true', 'false', and their variations, as well as
    empty strings.

    Parameters
    ----------
    name : str
        Name of the input to retrieve.
    required : bool, optional
        Whether the input is required. Defaults to False.
    trim_whitespace : bool, optional
        Whether to trim whitespace from the input. Defaults to True.

    Returns
    -------
    bool
        The boolean value of the input.

    Raises
    ------
    ValueError
        If the input is required but not provided.

    Examples
    --------
    >>> is_enabled = get_boolean_input('enable_feature', required=True)
    """

    input_value = get_input(
        name,
        required=required,
        trim_whitespace=trim_whitespace
    ).lower()

    if not input_value and not required:
        return False

    in_bool_true = input_value in BOOLEAN_TRUE

    if not in_bool_true or not input_value in BOOLEAN_FALSE:
        raise ValueError(f'Invalid boolean input for {name}: {input_value}')

    return in_bool_true


def set_output(name: str, value: IOValue) -> None:
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

    if environ_contains('GITHUB_OUTPUT'):
        return emit_file_command(
            'OUTPUT',
            utils.prepare_key_value_message(name, value)
        )

    sys.stdout.write(os.linesep)
    emit_command(
        name=GithubCommand.SET_OUTPUT,
        message=utils.prepare_key_value_message(name, value)
    )


def set_echo(enabled: bool) -> None:
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
    >>> set_echo(enabled=True)

    >>> # Disable command echoing (default)
    >>> set_echo(enabled=False)
    """
    emit(name=GithubCommand.ECHO, message='on' if enabled else 'off')


def set_fail(message: str | Exception) -> None:
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
    return os.getenv('RUNNER_DEBUG', '0') == '1'


def debug(message: str) -> None:
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
    emit_command(GithubCommand.DEBUG, {}, message=message)


def error(message: StringOrException, *, properties: AnnotationProperties | None = None) -> None:
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
    ...         message=e, properties=AnnotationProperties(title='Processing Error', file='processor.py', startLine=102)
    ...     )
    """
    props = properties or AnnotationProperties()
    cmd_properties = utils.to_command_properties(
        annotation_properties=props  # type: ignore
    )
    emit_command(
        GithubCommand.ERROR,
        properties=cmd_properties,
        message=str(message)
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
    ...     properties=AnnotationProperties(title='Config Change', file='config.yaml', startLine=10),
    ... )
    """
    props = properties or AnnotationProperties()
    cmd_properties = utils.to_command_properties(
        annotation_properties=props  # type: ignore
    )
    emit_command(
        GithubCommand.NOTICE,
        properties=cmd_properties,
        message=message
    )


def warning(message: StringOrException, *, properties: AnnotationProperties | None = None) -> None:
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
    ...     properties=AnnotationProperties(title='Resource Warning', file='disk_check.py', startLine=45),
    ... )
    """

    props = properties or AnnotationProperties()
    cmd_properties = utils.to_command_properties(
        annotation_properties=props  # type: ignore
    )

    emit_command(
        GithubCommand.WARNING,
        properties=cmd_properties,
        message=str(message)
    )


def start_group(name: str) -> None:
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
    emit(GithubCommand.GROUP, message=name)


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
    emit(GithubCommand.ENDGROUP)


@contextmanager
def group(name: str):
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
    start_group(name)
    try:
        yield
    finally:
        end_group()


__all__ = [
    'emit_command',
    'emit',
    'emit_file_command',
    'export_variable',
    'set_secret',
    'add_path',
    'get_input',
    'get_multiline_input',
    'get_boolean_input',
    'set_output',
    'set_echo',
    'set_fail',
    'is_debug',
    'debug',
    'error',
    'notice',
    'warning',
    'start_group',
    'end_group',
    'group',
    'AnnotationProperties'
]
