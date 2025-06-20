'''
**exec.exceptions**

Exceptions for command execution failures.
'''
from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from action_toolkit.corelib.exception import BaseActionError

if TYPE_CHECKING:
    from subprocess import CalledProcessError, TimeoutExpired


class ExecError(BaseActionError):
    '''
    Base class for command execution errors.
    '''
    pass


class InvalidCommandError(ExecError):
    '''
    Exception raised when an invalid command is provided.

    This is used to indicate that the command string is malformed or
    cannot be executed.
    '''

    def __init__(self, input_cmd: Sequence[str]) -> None:
        '''
        Initialize InvalidCommandError.

        Parameters
        ----------
        message : str
            The error message describing the invalid command.
        '''
        super().__init__(
            message=f'{" ".join(input_cmd)} is not a valid command.'
        )

class CommandFailedError(ExecError):
    '''
    Exception raised when command execution fails.

    Provides detailed information about the failed command including
    exit code, stdout, stderr, and the original command.
    '''

    def __init__(
        self,
        *,
        command: str,
        exit_code: int,
        stdout: str = '',
        stderr: str = '',
        message: str | None = None
    ) -> None:
        '''
        Initialize ExecError.

        Parameters
        ----------
        command : str
            The command that failed.
        exit_code : int
            The process exit code.
        stdout : str
            Standard output from the process.
        stderr : str
            Standard error from the process.
        message : str | None
            Optional custom error message.
        '''
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

        if message:
            error_msg = message
        else:
            error_msg = f'Command failed with exit code {exit_code}: {command}'
            if stderr:
                error_msg += f'\nStderr: {stderr.strip()}'

        super().__init__(error_msg)

    @classmethod
    def from_called_process_error(
        cls,
        error: CalledProcessError,
        command: str | None = None
    ) -> 'ExecError':
        '''
        Create ExecError from subprocess.CalledProcessError.

        Parameters
        ----------
        error : CalledProcessError
            The subprocess error.
        command : str | None
            Optional command string (if different from error.cmd).

        Returns
        -------
        ExecError
            The converted error.
        '''
        cmd = command or str(error.cmd)
        return cls(
            command=cmd,
            exit_code=error.returncode,
            stdout=error.stdout or '',
            stderr=error.stderr or ''
        )

    def __str__(self) -> str:
        '''String representation of the error.'''
        lines = [f'Command failed: {self.command}']
        lines.append(f'Exit code: {self.exit_code}')

        if self.stdout:
            lines.append(f'Stdout:\n{self.stdout}')

        if self.stderr:
            lines.append(f'Stderr:\n{self.stderr}')

        return '\n'.join(lines)


class CommandNotFoundError(CommandFailedError):
    '''
    Raised when a command cannot be found in PATH.

    This is a more specific version of ExecError for missing commands.
    '''

    def __init__(self, *, command: str, message: str | None = None) -> None:
        '''
        Initialize CommandNotFoundError.

        Parameters
        ----------
        command : str
            The command that wasn't found.
        message : str | None
            Optional custom message.
        '''
        if message is None:
            message = f'Command not found: {command}'

        super().__init__(
            command=command,
            exit_code=-1,
            message=message
        )


class CommandTimeoutError(CommandFailedError):
    '''
    Raised when a command exceeds its timeout.

    This wraps subprocess.TimeoutExpired with our error interface.
    '''

    def __init__(
        self,
        *,
        command: str,
        timeout: float,
        stdout: str = '',
        stderr: str = '',
        message: str | None = None
    ) -> None:
        '''
        Initialize CommandTimeoutError.

        Parameters
        ----------
        command : str
            The command that timed out.
        timeout : float
            The timeout value in seconds.
        stdout : str
            Any stdout captured before timeout.
        stderr : str
            Any stderr captured before timeout.
        message : str | None
            Optional custom message.
        '''
        self.timeout = timeout

        if message is None:
            message = f'Command timed out after {timeout} seconds: {command}'

        super().__init__(
            command=command,
            exit_code=-1,
            stdout=stdout,
            stderr=stderr,
            message=message
        )



__all__ = [
    'ExecError',
    'CommandNotFoundError',
    'CommandTimeoutError'
]