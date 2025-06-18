

from action_toolkit.core.internals.exceptions import CoreActionError


class ExecError(CoreActionError):
    '''Exception raised when process execution fails.'''

    def __init__(
        self,
        *,
        command: str,
        exit_code: int,
        stdout: str = '',
        stderr: str = '',
        message: str = ''
    ) -> None:
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

        if not message:
            message = f'Command "{command}" failed with exit code {exit_code}'

        super().__init__(message)