'''
**core.inputs**

Functions related to retrieving action inputs

'''

import os

from .internals.exceptions import InputError
from .internals.utils import (
    get_input_name,
    parse_yaml_boolean,
    split_lines
)

__all__ = [
    'get_input',
    'get_multiline_input',
    'get_bool_input'
]

def get_input(
    name: str,
    *,
    required: bool = False,
    trim_whitespace: bool = True
) -> str:
    '''
    Get the value of an action input.

    This function mirrors getInput in core.ts. It reads input values
    from environment variables set by GitHub Actions.

    Parameters
    ----------
    name : str
        Name of the input to get.
    options : Optional[InputOptions]
        Options for retrieving the input:
        - required: Whether the input is required (raises if missing)
        - trimWhitespace: Whether to trim whitespace (default: True)

    Returns
    -------
    str
        The input value.

    Raises
    ------
    InputError
        If the input is required but not supplied.

    Examples
    --------
    >>> # Get optional input
    >>> value = get_input(name='my-input')

    >>> # Get required input
    >>> value = get_input(
    ...     name='api-key',
    ...     options=InputOptions(required=True)
    ... )

    >>> # Get input without trimming whitespace
    >>> value = get_input(
    ...     name='formatted-text',
    ...     options=InputOptions(trimWhitespace=False)
    ... )
    '''
    env_name = get_input_name(name)
    val = os.environ.get(env_name, '')

    if required and not val:
        raise InputError(
            input_name=name,
            input_value=val,
            reason=f"Input '{name}' is required but not provided."
        )

    if trim_whitespace and val:
        val = val.strip()

    return val


def get_multiline_input(
    name: str,
    *,
    required: bool = False,
    trim_whitespace: bool = True,
    skip_empty_lines: bool = True
) -> list[str]:
    '''
    Get the values of a multiline input.

    This function mirrors getMultilineInput in core.ts. Each line
    of the input value is returned as a separate list element.

    Parameters
    ----------
    name : str
        Name of the input to get.
    options : Optional[MultilineInputOptions]
        Options for retrieving the input, including:
        - All options from InputOptions
        - skipEmptyLines: Whether to filter empty lines (default: True)

    Returns
    -------
    list[str]
        List of input values (one per line).

    Examples
    --------
    >>> # Input value: "line1\\nline2\\n\\nline3"
    >>> lines = get_multiline_input(name='files')
    >>> # Returns: ['line1', 'line2', 'line3']

    >>> # Include empty lines
    >>> lines = get_multiline_input(
    ...     name='files',
    ...     options=MultilineInputOptions(skipEmptyLines=False)
    ... )
    >>> # Returns: ['line1', 'line2', '', 'line3']
    '''

    value = get_input(
        name,
        required=required,
        trim_whitespace=trim_whitespace
    )

    lines = split_lines(value, skip_empty=skip_empty_lines)

    if trim_whitespace:
        lines = list(map(str.strip, lines))

    return lines


def get_bool_input(
    name: str,
    *,
    required: bool = False,
    trim_whitespace: bool = True
) -> bool:
    '''
    Get the value of an input as a boolean.

    This function mirrors getBooleanInput in core.ts. Boolean values
    are parsed according to YAML 1.2 specification.

    Parameters
    ----------
    name : str
        Name of the input to get.
    options : Optional[InputOptions]
        Options for retrieving the input.

    Returns
    -------
    bool
        Boolean value of the input.
        True for: 'true', 'True', 'TRUE', 'yes', 'Yes', 'YES',
                'y', 'Y', 'on', 'On', 'ON', '1'
        False for all other values.

    Examples
    --------
    >>> # Input value: "true"
    >>> enabled = get_boolean_input(name='enable-feature')
    >>> # Returns: True

    >>> # Input value: "yes"
    >>> confirmed = get_boolean_input(name='confirm')
    >>> # Returns: True

    >>> # Input value: "0"
    >>> debug = get_boolean_input(name='debug')
    >>> # Returns: False
    '''
    val = get_input(
        name=name,
        required=required,
        trim_whitespace=trim_whitespace
    )
    return parse_yaml_boolean(val)
