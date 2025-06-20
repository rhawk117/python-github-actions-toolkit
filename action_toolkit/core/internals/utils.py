"""
**core.internals.utils**
Utilities for GitHub Actions command handling, equivalent to utils.ts in TypeScript.

This module provides utility functions for converting values and properties
from strings to command values, handling annotations, and parsing inputs.
"""

from __future__ import annotations

from action_toolkit.corelib.types.core import YAML_BOOLEAN_TRUE


def parse_yaml_boolean(value: str) -> bool:
    """
    Parse a boolean value according to YAML 1.2 specification.

    This utility function is used internally by getBooleanInput
    to parse boolean strings consistently with GitHub Actions.

    These are "truthy" values according to YAML and have types
    definied which you can find in types.py which are also below
    for convenience:
    ```python
    YAML_BOOLEAN_TRUE = frozenset(['true', 'yes', 'on', 'y', '1'])
    YAML_BOOLEAN_FALSE = frozenset(['false', 'no', 'off', 'n', '0'])
    ```

    Parameters
    ----------
    value : str
        The string value to parse.

    Returns
    -------
    bool
        True if the value is a YAML truthy value, False otherwise.

    Notes
    -----
    Truthy values (case-insensitive): true, yes, on, y, 1
    All other values are considered False.

    Examples
    --------
    >>> parse_boolean('true')
    True

    >>> parse_boolean('YES')
    True

    >>> parse_boolean('1')
    True

    >>> parse_boolean('false')
    False

    >>> parse_boolean('anything else')
    False
    """
    return value.lower() in YAML_BOOLEAN_TRUE


def get_input_name(name: str) -> str:
    """
    Converts an input name to its environment variable form.

    GitHub Actions converts input names to uppercase environment
    variables prefixed with INPUT_. This function performs that
    conversion.

    Parameters
    ----------
    name : str
        The input name to convert.

    Returns
    -------
    str
        The environment variable name.

    Examples
    --------
    >>> get_input_name('my-input')
    'INPUT_MY_INPUT'

    >>> get_input_name('my input name')
    'INPUT_MY_INPUT_NAME'
    """
    normalized = name.upper().replace(' ', '_').replace('-', '_')
    return f'INPUT_{normalized}'


def split_lines(input: str, *, skip_empty: bool = True) -> list[str]:
    """
    Split a multiline string into individual lines.

    This utility is used by getMultilineInput to process
    multiline input values.

    Parameters
    ----------
    input : str
        The multiline string to split.
    skip_empty : bool
        Whether to filter out empty lines. Default is True.

    Returns
    -------
    list[str]
        List of individual lines.

    Examples
    --------
    >>> split_lines('line1\\nline2\\n\\nline3')
    ['line1', 'line2', 'line3']

    >>> split_lines('line1\\nline2\\n\\nline3', skip_empty=False)
    ['line1', 'line2', '', 'line3']
    """
    lines = input.split('\n')

    if skip_empty:
        return list(filter(lambda line: line.strip() != '', lines))

    return lines


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.

    Used internally for validation of certain inputs.

    Parameters
    ----------
    url : str
        The string to validate.

    Returns
    -------
    bool
        True if the string is a valid URL, False otherwise.
    """
    try:
        from urllib.parse import urlparse

        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
