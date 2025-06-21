
from __future__ import annotations
import json
import os
from typing import TYPE_CHECKING, Any, Final
from action_toolkit.corelib.utils import dataclass_utils

if TYPE_CHECKING:
    from .models import (
        CommandPropertyValue, CommandValue, AnnotationProperties, Command
    )

__all__ = [
    'get_command_string',
    'to_command_value',
    'to_command_properties',
    'prepare_key_value_message'
]

_COMMAND_SEP: Final[str] = '::'


def _key_value_delimiter() -> str:
    '''
    the way to delimit key-value pairs for file commands,
    in own function if this ever is updated and mirrors
    the TypeScript implementation

    Returns
    -------
    str
        _the key value delimiter_
    '''
    return f'ghadelimiter_{os.urandom(16).hex()}'


def _replace_list(input_str: str, replacements: list[tuple[str, str]]) -> str:
    result = input_str
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def _escape_data(s: Any) -> str:
    """
    Escape special characters in command data.
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
    """
    return _replace_list(to_command_value(input=s), [
        ('%', '%25'),
        ('\r', '%0D'),
        ('\n', '%0A')
    ])


def _escape_prop(s: Any) -> str:
    """
    Escape special characters in command properties.

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
    """
    return _replace_list(to_command_value(input=s), [
        ('%', '%25'),
        ('\r', '%0D'),
        ('\n', '%0A'),
        (':', '%3A'),
        (',', '%2C')
    ])


def _stringify_cmd_props(properties: dict[str, CommandPropertyValue]) -> str:
    """
    Convert command properties to a string format.

    Parameters
    ----------
    properties : dict[str, CommandPropertyValue]
        Dictionary of command properties.

    Returns
    -------
    str
        String representation of the command properties.
        Format: 'key1=value1,key2=value2,...'
    """
    property_parts = []
    for key, value in properties.items():
        if value is None:
            continue
        property_parts.append(f'{key}={_escape_prop(value)}')

    return ','.join(property_parts) if property_parts else ''


def get_command_string(cmd: Command) -> str:
    '''
    Converts a Command object to a string
    that is escaped, formatted and ready
    to be emitted to standard output stream

    Parameters
    ----------
    cmd : Command
        _the command object_

    Returns
    -------
    str
        _the prepared command string_
    '''
    cmd_string = f'{cmd.command.value}{_COMMAND_SEP}'
    if cmd.properties:
        prop_string = _stringify_cmd_props(cmd.properties)
        if prop_string:
            cmd_string += ' ' + prop_string

    cmd_string += _COMMAND_SEP + _escape_data(cmd.message)
    return cmd_string


def to_command_value(input: CommandValue) -> str:
    """
    Sanitizes a command input value into a string.

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
    """
    if input is None:
        return ''

    if isinstance(input, str):
        return input

    try:
        return json.dumps(input, separators=(',', ':'), ensure_ascii=False)
    except (TypeError, ValueError):
        return str(input)


def to_command_properties(annotation_properties: AnnotationProperties) -> dict[str, CommandPropertyValue]:
    '''
    Converts an AnnotationProperties object to a dictionary of command properties
    and renames the `startLine` and `startColumn` properties to `line` and `col`

    Parameters
    ----------
    annotation_properties : AnnotationProperties
        _the annotation properties_

    Returns
    -------
    dict[str, CommandPropertyValue]
        _the normalized dictionary_
    '''
    # 'startLine', # should be mapped to 'line'
    # 'startColumn', # should be mapped to 'col'
    cmd_props = dataclass_utils.dump_dataclass(
        annotation_properties,
        exclude_none=True,
        exclude={'startLine', 'startColumn'}
    )

    if annotation_properties.startLine is not None:
        cmd_props['line'] = annotation_properties.startLine

    if annotation_properties.startColumn is not None:
        cmd_props['col'] = annotation_properties.startColumn

    return cmd_props


def no_way_that_just_happened(delimiter: str) -> ValueError:
    '''lol'''
    return ValueError(
        f'Key contains the delimiter "{delimiter}", which is not allowed.'
        'How did this even happen?'
    )
    
def prepare_key_value_message(
    key: str,
    value: CommandValue
) -> CommandValue:
    """
    Prepares a key-value message for command properties.

    Parameters
    ----------
    key : str
        The key for the property.
    value : CommandValue
        The value for the property.

    Returns
    -------
    CommandValue
        The formatted key-value message.
    """
    
    converted_value = to_command_value(value)
    delimiter = _key_value_delimiter()
    
    if key in delimiter:
        raise no_way_that_just_happened(delimiter)
    
    if delimiter in converted_value:
        raise no_way_that_just_happened(delimiter)
    
    return f'{key}<<{delimiter}{os.linesep}{converted_value}{os.linesep}{delimiter}'


