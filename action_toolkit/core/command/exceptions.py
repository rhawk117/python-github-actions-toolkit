"""
**core.internals.exceptions**
exceptions for the GitHub Actions toolkit core package.
"""

from action_toolkit.corelib.exception import BaseActionError

INPUT_EXC_FORMAT = 'InputError: Input "{input_name}" with value "{input_value}" is invalid. {reason}.'


class CommandsError(BaseActionError):
    """
    Base exception for GitHub Actions errors.

    This is the base class for all exceptions raised by the toolkit.
    """

    pass


class InputError(CommandsError):
    """
    Exception raised for input-related errors.

    Typically raised when a required input is missing or invalid.
    """

    def __init__(self, *, input_name: str, input_value: str, reason: str = '') -> None:
        message = INPUT_EXC_FORMAT.format(input_name=input_name, input_value=input_value, reason=reason)
        super().__init__(message=message)


class AnnotationError(CommandsError):
    """
    Exception raised for annotation-related errors.

    Raised when annotation properties violate constraints.
    """

    pass

class EnvironError(Exception):

    def __init__(self, message: str) -> None:
        """
        Initialize the EnvironError.

        Args:
            message: The error message to display.
        """
        super().__init__(f'action_toolkit.EnvironError: {message}')
