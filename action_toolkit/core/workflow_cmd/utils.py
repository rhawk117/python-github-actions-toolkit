
from __future__ import annotations

import json
from typing import TYPE_CHECKING
from action_toolkit.internals import dataclass_utils

if TYPE_CHECKING:
    from ..types import CommandValue, CommandPropertyValue, AnnotationProperties
    from typing import Any


def to_command_value(*, input: CommandValue) -> str:
    '''
    Sanitizes an input into a string for safe command passing.

    mirrors toCommandValue in utils.ts, converting
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


def to_command_properties(
    annotation_properties: AnnotationProperties
) -> dict[str, CommandPropertyValue]:
    '''
    Convert annotation properties to command properties format.

    This function mirrors toCommandProperties in utils.ts, mapping
    the annotation property names to the command property names
    expected by the GitHub Actions runner.

    Parameters
    ----------
    annotation_properties : AnnotationProperties
        The annotation properties to convert.

    Returns
    -------
    dict[str, CommandPropertyValue]
        Command properties dictionary with mapped keys:
        - title -> title
        - file -> file
        - startLine -> line
        - endLine -> endLine
        - startColumn -> col
        - endColumn -> endColumn

    See Also
    --------
    IssueCommandProperties in the GitHub Actions runner:
    https://github.com/actions/runner/blob/main/src/Runner.Worker/ActionCommandManager.cs#L646

    Examples
    --------
    >>> from types import AnnotationProperties
    >>> props = AnnotationProperties(
    ...     title='Error',
    ...     file='main.py',
    ...     startLine=42
    ... )
    >>> to_command_properties(annotation_properties=props)
    {'title': 'Error', 'file': 'main.py', 'line': 42}
    '''
    command_props: dict[str, CommandPropertyValue] = dataclass_utils.dump_dataclass(
        annotation_properties,
        exclude_none=True
    )
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