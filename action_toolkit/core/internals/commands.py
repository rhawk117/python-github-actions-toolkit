'''
**core.internals.commands**

Abstracts the command handling functionality for GitHub Actions.

'''
from __future__ import annotations

import os
import sys
import json
from typing import TYPE_CHECKING, Any, Literal, TextIO, Final
from action_toolkit.internals import dataclass_utils
from .types import AnnotationProperties, WorkflowCommand, CommandValue, CommandPropertyValue

CMD_STRING: Final[str] = '::'


__all__ = [
    'to_command_value',
    'to_command_properties',
    'issue_command',
    'issue',
    'issue_file_command',
    'prepare_key_value_message'
]

def to_command_value(*, input: CommandValue) -> str:
    '''
    Sanitizes an input into a string for safe command passing.

    mirrors toCommandValue in ts, converting
    various input types to strings suitable for GitHub Actions commands.

    Parameters
    ----------
    input : CommandValue
        The input value to sanitize. Can be None, string, or any
        JSON-serializable value.

    Returns
    -------
    str
        Sanitized string representation of the input:
        - None -> ''
        - str -> unchanged
        - Other types -> JSON serialized

    Examples
    --------
    >>> to_command_value(input=None)
    ''

    >>> to_command_value(input='hello world')
    'hello world'

    >>> to_command_value(input={'key': 'value'})
    '{"key": "value"}'

    >>> to_command_value(input=[1, 2, 3])
    '[1, 2, 3]'
    '''
    if input is None:
        return ''

    if isinstance(input, str):
        return input

    try:
        return json.dumps(input, separators=(',', ':'), ensure_ascii=False)
    except (TypeError, ValueError):
        return str(input)


def to_command_properties(annotation_properties: AnnotationProperties) -> dict[str, CommandPropertyValue]:
    command_props: dict[str, CommandPropertyValue] = {}

    if annotation_properties.title is not None:
        command_props['title'] = annotation_properties.title

    if annotation_properties.file is not None:
        command_props['file'] = annotation_properties.file

    if annotation_properties.startLine is not None:
        command_props['line'] = annotation_properties.startLine  # Map startLine -> line

    if annotation_properties.endLine is not None:
        command_props['endLine'] = annotation_properties.endLine

    if annotation_properties.startColumn is not None:
        command_props['col'] = annotation_properties.startColumn  # Map startColumn -> col

    if annotation_properties.endColumn is not None:
        command_props['endColumn'] = annotation_properties.endColumn

    return command_props

def escape_data(s: Any) -> str:
    '''
    Escape special characters in command data.

    This function mirrors escapeData in command.ts, ensuring that
    command messages are properly escaped for the GitHub Actions runner.

    Parameters
    ----------
    s : Any
        Data to escape. Will be converted to string first.

    Returns
    -------
    str
        The escaped string with special characters replaced:
        - % -> %25
        - \\r -> %0D
        - \\n -> %0A

    Examples
    --------
    >>> escape_data('Hello\\nWorld')
    'Hello%0AWorld'

    >>> escape_data('100% complete')
    '100%25 complete'
    '''
    return (
        to_command_value(input=s)
            .replace('%', '%25')
            .replace('\r', '%0D')
            .replace('\n', '%0A')
    )


def escape_property(s: Any) -> str:
    '''
    Escape special characters in command properties.

    This function mirrors escapeProperty in command.ts, providing
    additional escaping for property values.

    Parameters
    ----------
    s : Any
        Property value to escape. Will be converted to string first.

    Returns
    -------
    str
        The escaped string with special characters replaced:
        - % -> %25
        - \\r -> %0D
        - \\n -> %0A
        - : -> %3A
        - , -> %2C

    Examples
    --------
    >>> escape_property('key:value')
    'key%3Avalue'

    >>> escape_property('item1,item2')
    'item1%2Citem2'
    '''
    return (
        to_command_value(input=s)
            .replace('%', '%25')
            .replace('\r', '%0D')
            .replace('\n', '%0A')
            .replace(':', '%3A')
            .replace(',', '%2C')
    )


class Command:
    '''
    Represents an Actions workflow command.

    This class mirrors the Command class in command.ts, providing
    the same command formatting functionality for the GitHub Actions
    runner.

    Parameters
    ----------
    command : str
        The command name to issue.
    properties : Dict[str, CommandPropertyValue]
        Additional properties / options for the command as key-value pairs.
    message : CommandValue
        The message to include with the command.

    Examples
    --------
    >>> cmd = Command(command='warning', properties={}, message='This is a warning')
    >>> str(cmd)
    '::warning::This is a warning'

    >>> cmd = Command(
    ...     command='set-output',
    ...     properties={'name': 'result'},
    ...     message='success'
    ... )
    >>> str(cmd)
    '::set-output name=result::success'
    '''

    def __init__(
        self,
        *,
        command: WorkflowCommand,
        properties: dict[str, CommandPropertyValue],
        message: CommandValue
    ) -> None:
        '''Initialize a Command instance.'''
        self.command = command.value if isinstance(command, WorkflowCommand) else command
        self.properties = properties
        self.message = message


    def as_string(self) -> str:
        '''
        Convert the command to its string representation.

        Returns
        -------
        str
            The formatted command string in the format:
            ::command key=value,key=value::message
        '''
        cmd_str = f'{CMD_STRING}{self.command}'

        if self.properties:
            prop_parts = []
            for key, value in self.properties.items():
                if value is not None:
                    prop_parts.append(f'{key}={escape_property(value)}')

            if prop_parts:
                cmd_str += ' ' + ','.join(prop_parts)

        cmd_str += f'{CMD_STRING}{escape_data(self.message)}'
        return cmd_str


    def write(self, file: TextIO | None = None) -> None:
        '''
        Write a command to the output stream.

        Parameters
        ----------
        cmd : Command
            The command to write.
        file : Optional[TextIO]
            The output stream to write to. Defaults to sys.stdout.
        '''
        if file is None:
            file = sys.stdout

        file.write(self.as_string() + os.linesep) # type: ignore
        file.flush() # type: ignore


    def __repr__(self) -> str:
        '''Return a detailed string representation for debugging.'''
        return (
            f'Command(command={self.command!r}, '
            f'properties={self.properties!r}, '
            f'message={self.message!r})'
        )


# ** public API functions **

def issue_command(
    *,
    command: WorkflowCommand,
    properties: dict[str, CommandPropertyValue] | None = None,
    message: CommandValue = ''
) -> None:
    '''
    Issues a command to the Actions runner.

    This function mirrors issueCommand function in command.ts.
    It outputs a specially formatted string to stdout that the Actions
    runner interprets as a command.

    Parameters
    ----------
    command : str
        The command name to issue (e.g., 'warning', 'error', 'set-output').
    properties : Optional[Dict[str, CommandPropertyValue]]
        Additional properties for the command as key-value pairs.
        Defaults to an empty dict.
    message : CommandValue
        The message to include with the command. Can be any JSON-serializable
        value. Defaults to empty string.

    Notes
    -----
    Command Format:
        ::name key=value,key=value::message

    The function writes to stdout and flushes to ensure the command
    is immediately visible to the GitHub Actions runner.

    Examples
    --------
    >>> # Issue a warning annotation
    >>> issue_command(command='warning', message='This is a warning message')
    # Output: ::warning::This is a warning message

    >>> # Set an environment variable
    >>> issue_command(
    ...     command='set-env',
    ...     properties={'name': 'MY_VAR'},
    ...     message='some value'
    ... )
    # Output: ::set-env name=MY_VAR::some value

    >>> # Add a secret mask
    >>> issue_command(command='add-mask', message='secretValue123')
    # Output: ::add-mask::secretValue123
    '''
    if properties is None:
        properties = {}

    cmd = Command(
        command=command,
        properties=properties,
        message=message
    )
    cmd.write()


def issue(*, name: WorkflowCommand, message: str = '') -> None:
    '''
    Issue a simple command without properties.

    This is a convenience function that mirrors the issue function
    in command.ts for commands that don't require properties.

    Parameters
    ----------
    name : str
        The command name to issue.
    message : str
        The message to include with the command. Defaults to empty string.

    Examples
    --------
    >>> issue(name='debug', message='Debug message')
    # Output: ::debug::Debug message

    >>> issue(name='endgroup')
    # Output: ::endgroup::
    '''
    issue_command(command=name, properties={}, message=message)


def issue_file_command(
    command: Literal['STATE', 'OUTPUT', 'ENV'],
    message: str,
    *,
    env_var: str | None = None,
    file_path: str | None = None
) -> str:
    '''
    Issue a command by writing to a file.

    This is used for newer style GitHub Actions commands that write
    to files instead of stdout (e.g., GITHUB_OUTPUT, GITHUB_ENV).

    Parameters
    ----------
    command : str
        The type of file command (e.g., 'OUTPUT', 'ENV').
    message : str
        The formatted message to write to the file.
    env_var : Optional[str]
        The environment variable containing the file path.
    file_path : Optional[str]
        Direct file path to use (overrides env_var).

    Raises
    ------
    ValueError
        If neither env_var nor file_path is provided, or if the
        file path cannot be determined.
    '''
    if file_path is None:
        if env_var is None:
            raise ValueError('Either env_var or file_path must be provided')
        file_path = os.environ.get(env_var, '')

    if not file_path:
        raise ValueError(f'Unable to find file path for command {command}')

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    file_cmd = message + os.linesep
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(file_cmd)
    return file_cmd


def prepare_key_value_message(key: str, value: Any) -> str:
    '''
    Prepare a key-value message for file commands.

    This formats messages for the newer file-based command style
    used with GITHUB_OUTPUT and GITHUB_ENV.

    Parameters
    ----------
    key : str
        The key/name for the value.
    value : Any
        The value to set.

    Returns
    -------
    str
        The formatted message with proper delimiters and escaping.
    '''
    converted_value = to_command_value(input=value)

    delimiter = f'ghadelimiter_{os.urandom(16).hex()}'

    # format: key<<delimiter\nvalue\ndelimiter
    return f'{key}<<{delimiter}{os.linesep}{converted_value}{os.linesep}{delimiter}'