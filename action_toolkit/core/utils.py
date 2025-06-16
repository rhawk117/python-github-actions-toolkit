'''
**utils.py** - Utility functions for the Action Toolkit, re-write in python

'''

from __future__ import annotations
import json
from typing import Any
try:
    from typing import TypedDict, NotRequired  # Python 3.11+
except ImportError:
    from typing_extensions import TypedDict, NotRequired  # Python 3.8-3.10


class AnnotationProperties(TypedDict):
    '''Properties for workflow command annotations'''
    title: NotRequired[str]
    file: NotRequired[str]
    startLine: NotRequired[int]
    endLine: NotRequired[int]
    startColumn: NotRequired[int]
    endColumn: NotRequired[int]


CommandProperties = dict[str, Any]


def to_command_value(*, input: Any) -> str:
    '''
    Sanitizes an input into a string so it can be passed into issue_command safely

    Args:
        input: Input value to sanitize into a string

    Returns:
        Sanitized string representation of the input
    '''
    if input is None:
        return ''

    elif isinstance(input, str):
        return input

    return json.dumps(input)


def to_command_properties(*, annotation_properties: AnnotationProperties) -> CommandProperties:
    '''
    Converts annotation properties to command properties format

    Args:
        annotation_properties: Annotation properties to convert

    Returns:
        Command properties dictionary for the annotation command

    See IssueCommandProperties: https://github.com/actions/runner/blob/main/src/Runner.Worker/ActionCommandManager.cs#L646
    '''
    if not annotation_properties:
        return {}

    command_props: CommandProperties = {}

    props = ('title', 'file', 'line', 'endLine', 'col', 'endColumn')
    for prop in props:
        if not prop in annotation_properties:
            continue
        command_props[prop] = annotation_properties[prop] # type: ignore[assignment]
    return command_props