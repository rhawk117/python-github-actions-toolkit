
EXC_FORMAT = 'PyActionToolkit.{name}: {message}.\n<cause={cause}>'

class BaseActionError(Exception):
    '''
    Base exception for the Action Toolkit.

    This is the base class for all exceptions raised by the toolkit.
    It is used to catch all toolkit-related errors in a single block.
    '''

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        '''
        Initialize the ActionToolkitError, base exception for all toolkit errors.

        Args:
            message: Optional error message.
            cause: Optional underlying exception that caused this error.
        '''
        self.message = EXC_FORMAT.format(
            name=self.__class__.__name__,
            message=message,
            cause=cause.__class__.__name__ if cause else 'N/A'
        )
        super().__init__(self.message)