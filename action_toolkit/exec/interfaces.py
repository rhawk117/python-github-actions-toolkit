from __future__ import annotations
import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

from action_toolkit.core.command import StringOrPathlib

if TYPE_CHECKING:
    from action_toolkit.corelib.types.io import StringOrPathlib
    from collections.abc import Mapping, Callable


@dataclasses.dataclass(slots=True)
class ExecOptions:
    '''
    Initialize execution options.

    Parameters
    ----------
    cwd : StringOrPathlib | None
        Working directory for the process.
    env : Mapping[str, str] | None
        Environment variables. If None, inherits current environment.
    input : str | bytes | None
        Input to send to the process stdin.
    timeout : float | None
        Maximum execution time in seconds.
    silent : bool
        If True, suppresses stdout/stderr logging to Actions output.
    ignore_return_code : bool
        If True, doesn't raise ExecError on non-zero exit codes.
    fail_on_stderr : bool
        If True, treats any stderr output as failure.
    listeners : ExecListeners | None
        Callback functions for handling output streams.
    '''

    cwd: StringOrPathlib | None = None
    env: Mapping[str, str] | None = None
    input: str | bytes | None = None
    timeout: float | None = None
    silent: bool = False
    ignore_return_code: bool = False
    fail_on_stderr: bool = False

    def __post_init__(self) -> None:
        if self.cwd is not None:
            self.cwd = Path(self.cwd)
        if self.env is not None:
            self.env = dict(self.env)


@dataclasses.dataclass(slots=True)
class ExecListeners:
    '''
    Callbacks for handling process output for exec functions.
    Initialize execution listeners.

    Parameters
    ----------
    stdout : Callable[[str], None] | None
        Called for each line of stdout output.
    stderr : Callable[[str], None] | None
        Called for each line of stderr output.
    debug : Callable[[str], None] | None
        Called for debug messages during execution.
    '''

    stdout: Callable[[str], None] | None = None
    stderr: Callable[[str], None] | None = None
    debug: Callable[[str], None] | None = None

    def __post_init__(self) -> None:
        '''
        '''
        pass


@dataclasses.dataclass
class ExecResult:
    '''
    Wrapper class for process execution results.

    Parameters
    ----------
    exit_code : int
        Process exit code.
    stdout : str
        Standard output from the process.
    stderr : str
        Standard error from the process.
    command : str
        The command that was executed.
    '''

    exit_code: int
    stdout: str
    stderr: str
    command: str

    @property
    def success(self) -> bool:
        '''True if the process completed successfully.'''
        return self.exit_code == 0