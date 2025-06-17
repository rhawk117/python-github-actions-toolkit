

from action_toolkit.corelib.exception import BaseActionError


class ActionIOError(BaseActionError):
    """Base class for all IO-related errors in the action toolkit.

    This class is used to represent errors that occur during input/output operations
    within the action toolkit. It inherits from BaseActionError, which provides a
    common interface for all action-related errors.
    """
    pass
