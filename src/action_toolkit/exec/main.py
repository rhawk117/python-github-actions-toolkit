
from __future__ import annotations
import asyncio
from collections.abc import AsyncGenerator
import contextlib
import os
import subprocess
from typing import TYPE_CHECKING

from action_toolkit.corelib.types.io import StringOrPathlib

from .interfaces import ExecOptions, ExecListeners, ExecResult
from .exceptions import ExecError
from action_toolkit import core

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Generator

def exec(
    tool: str,
    args: Sequence[str] | None = None,
    *,
    options: ExecOptions | None = None,
    listeners: ExecListeners | None = None
) -> ExecResult:
    '''
    Executes a command synchronously.

    Parameters
    ----------
    tool : str
        The tool/command to execute.
    args : Sequence[str] | None
        Arguments to pass to the tool.
    options : ExecOptions | None
        Execution options.

    Returns
    -------
    ExecResult
        The execution result.

    Raises
    ------
    ExecError
        If the command fails and ignore_return_code is False.

    Examples
    --------
    >>> result = exec('git', ['status', '--porcelain'])
    >>> if result.success:
    ...     print(f"Git status: {result.stdout}")

    >>> # With custom options
    >>> options = ExecOptions(cwd='/tmp', silent=True)
    >>> result = exec('ls', ['-la'], options=options)
    '''
    options = options or ExecOptions()
    listeners = listeners or ExecListeners()
    command_parts = [tool] + list(args or [])
    command_str = ' '.join(command_parts)

    if not options.silent:
        core.debug(message=f'Executing: {command_str}')

    try:
        env = dict(os.environ)
        if options.env:
            env.update(options.env)

        process = subprocess.run(
            command_parts,
            cwd=options.cwd,
            env=env,
            input=options.input,
            capture_output=True,
            text=True,
            timeout=options.timeout,
            check=False
        )

        stdout = process.stdout or ''
        stderr = process.stderr or ''

        if listeners and listeners.stdout and stdout:
            for line in stdout.splitlines():
                listeners.stdout(line)

        if listeners.stderr and stderr:
            for line in stderr.splitlines():
                listeners.stderr(line)

        if not options.silent:
            if stdout.strip():
                for line in stdout.splitlines():
                    core.debug(message=f'stdout: {line}')

            if stderr.strip():
                for line in stderr.splitlines():
                    core.debug(message=f'stderr: {line}')

        result = ExecResult(
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            command=command_str
        )

        if not options.ignore_return_code and process.returncode != 0:
            raise ExecError(
                command=command_str,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr
            )

        if options.fail_on_stderr and stderr.strip():
            raise ExecError(
                command=command_str,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                message=f'Command "{command_str}" produced stderr output'
            )

        return result

    except subprocess.TimeoutExpired as e:
        raise ExecError(
            command=command_str,
            exit_code=-1,
            message=f'Command "{command_str}" timed out after {options.timeout}s'
        ) from e

    except FileNotFoundError as e:
        raise ExecError(
            command=command_str,
            exit_code=-1,
            message=f'Command "{tool}" not found'
        ) from e


async def exec_async(
    tool: str,
    args: Sequence[str] | None = None,
    *,
    options: ExecOptions | None = None,
    listeners: ExecListeners | None = None
) -> ExecResult:
    '''
    Executes a command asynchronously.

    Parameters
    ----------
    tool : str
        The tool/command to execute.
    args : Sequence[str] | None
        Arguments to pass to the tool.
    options : ExecOptions | None
        Execution options.

    Returns
    -------
    ExecResult
        The execution result.

    Raises
    ------
    ExecError
        If the command fails and ignore_return_code is False.

    Examples
    --------
    >>> import asyncio
    >>>
    >>> async def main():
    ...     result = await exec_async('git', ['log', '--oneline', '-5'])
    ...     print(f"Recent commits: {result.stdout}")
    >>>
    >>> asyncio.run(main())
    '''
    options = options or ExecOptions()
    listeners = listeners or ExecListeners()
    command_parts = [tool] + list(args or [])
    command_str = ' '.join(command_parts)

    if not options.silent:
        core.debug(message=f'Executing async: {command_str}')

    try:
        env = dict(os.environ)
        if options.env:
            env.update(options.env)

        process = await asyncio.create_subprocess_exec(
            *command_parts,
            cwd=options.cwd,
            env=env,
            stdin=asyncio.subprocess.PIPE if options.input else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        input_bytes = None
        if options.input:
            input_bytes = options.input.encode() if isinstance(options.input, str) else options.input

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(input_bytes),
            timeout=options.timeout
        )

        stdout = stdout_bytes.decode() if stdout_bytes else ''
        stderr = stderr_bytes.decode() if stderr_bytes else ''

        if listeners.stdout and stdout:
            for line in stdout.splitlines():
                listeners.stdout(line)

        if listeners.stderr and stderr:
            for line in stderr.splitlines():
                listeners.stderr(line)

        if not options.silent:
            if stdout.strip():
                for line in stdout.splitlines():
                    core.debug(message=f'stdout: {line}')

            if stderr.strip():
                for line in stderr.splitlines():
                    core.debug(message=f'stderr: {line}')

        result = ExecResult(
            exit_code=process.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            command=command_str
        )
        exit_status = process.returncode or 0
        if not options.ignore_return_code and exit_status != 0:
            raise ExecError(
                command=command_str,
                exit_code=exit_status,
                stdout=stdout,
                stderr=stderr
            )

        if options.fail_on_stderr and stderr.strip():
            raise ExecError(
                command=command_str,
                exit_code=exit_status,
                stdout=stdout,
                stderr=stderr,
                message=f'Command "{command_str}" produced stderr output'
            )

        return result

    except asyncio.TimeoutError as e:
        if process:
            process.terminate()
            await process.wait()

        raise ExecError(
            command=command_str,
            exit_code=-1,
            message=f'Command "{command_str}" timed out after {options.timeout}s'
        ) from e

    except FileNotFoundError as e:
        raise ExecError(
            command=command_str,
            exit_code=-1,
            message=f'Command "{tool}" not found'
        ) from e


@contextlib.contextmanager
def exec_context(
    *,
    cwd: StringOrPathlib | None = None,
    env: Mapping[str, str] | None = None
) -> Generator[ExecOptions, None, None]:
    '''Context manager for sharing execution options.

    Parameters
    ----------
    cwd : StringOrPath | None
        Working directory for all executions in this context.
    env : Mapping[str, str] | None
        Environment variables for all executions in this context.

    Yields
    ------
    ExecOptions
        Shared execution options.

    Examples
    --------
    >>> with exec_context(cwd='/tmp') as ctx:
    ...     result1 = exec('ls', options=ctx)
    ...     result2 = exec('pwd', options=ctx)
    '''
    options = ExecOptions(cwd=cwd, env=env)
    yield options


@contextlib.asynccontextmanager
async def exec_context_async(
    *,
    cwd: StringOrPathlib | None = None,
    env: Mapping[str, str] | None = None
) -> AsyncGenerator[ExecOptions, None]:
    '''Async context manager for sharing execution options.

    Parameters
    ----------
    cwd : StringOrPath | None
        Working directory for all executions in this context.
    env : Mapping[str, str] | None
        Environment variables for all executions in this context.

    Yields
    ------
    ExecOptions
        Shared execution options.

    Examples
    --------
    >>> async with exec_context_async(cwd='/tmp') as ctx:
    ...     result1 = await exec_async('ls', options=ctx)
    ...     result2 = await exec_async('pwd', options=ctx)
    '''
    options = ExecOptions(cwd=cwd, env=env)
    yield options


def get_exec_output(
    tool: str,
    args: Sequence[str] | None = None,
    *,
    options: ExecOptions | None = None,
    listeners: ExecListeners | None = None
) -> str:
    '''Execute a command and return only stdout.

    This is a convenience function for commands where you only care
    about the stdout output.

    Parameters
    ----------
    tool : str
        The tool/command to execute.
    args : Sequence[str] | None
        Arguments to pass to the tool.
    options : ExecOptions | None
        Execution options.

    Returns
    -------
    str
        The stdout output from the command.

    Raises
    ------
    ExecError
        If the command fails.

    Examples
    --------
    >>> git_status = get_exec_output('git', ['status', '--porcelain'])
    >>> current_dir = get_exec_output('pwd').strip()
    '''
    result = exec(tool, args, options=options, listeners=listeners)
    return result.stdout


async def get_exec_output_async(
    tool: str,
    args: Sequence[str] | None = None,
    *,
    options: ExecOptions | None = None
) -> str:
    '''Execute a command asynchronously and return only stdout.

    Parameters
    ----------
    tool : str
        The tool/command to execute.
    args : Sequence[str] | None
        Arguments to pass to the tool.
    options : ExecOptions | None
        Execution options.

    Returns
    -------
    str
        The stdout output from the command.

    Raises
    ------
    ExecError
        If the command fails.

    Examples
    --------
    >>> git_branch = await get_exec_output_async('git', ['branch', '--show-current'])
    >>> python_version = await get_exec_output_async('python', ['--version'])
    '''
    result = await exec_async(tool, args, options=options)
    return result.stdout



__all__ = [
    'exec',
    'exec_async',
    'exec_context',
    'exec_context_async',
    'get_exec_output',
    'get_exec_output_async',
    'ExecError',
    'ExecOptions',
    'ExecListeners',
    'ExecResult'
]