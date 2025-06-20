'''
**exec.main**

Pythonic utility functions for executing commands with enhanced subprocess management,
pipeline support, and GitHub Actions integration.
'''
from __future__ import annotations

import asyncio
from calendar import c
from collections.abc import Generator
import contextlib
import os
import selectors
import shlex
from sqlite3 import Time
import subprocess
import sys
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, overload

from action_toolkit import core

from .exceptions import CommandTimeoutError, ExecError, CommandNotFoundError, InvalidCommandError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
    from subprocess import CompletedProcess

    from action_toolkit.corelib.types.io import StringOrPathlib


class ProcessResult:
    '''
    Enhanced wrapper around subprocess.CompletedProcess with additional utilities.

    Provides a more Pythonic interface with properties for common operations
    and pipeline support.
    '''

    def __init__(
        self,
        *,
        completed_process: CompletedProcess[str],
        command: str | list[str]
    ) -> None:
        '''
        Parameters
        ----------
        completed_process : CompletedProcess[str]
            The completed process from subprocess.
        command : str | list[str]
            The original command that was executed.
        '''
        self._process = completed_process
        self._command = command if isinstance(command, str) else shlex.join(command)

    @property
    def completed_process(self) -> CompletedProcess[str]:
        '''The underlying subprocess.CompletedProcess object.'''
        return self._process

    @property
    def returncode(self) -> int:
        '''Process return code.'''
        return self._process.returncode

    @property
    def stdout(self) -> str:
        '''Standard output as string.'''
        return self._process.stdout or ''

    @property
    def stderr(self) -> str:
        '''Standard error as string.'''
        return self._process.stderr or ''

    @property
    def success(self) -> bool:
        '''True if the process completed successfully (returncode == 0).'''
        return self.returncode == 0

    @property
    def failed(self) -> bool:
        '''True if the process failed (returncode != 0).'''
        return not self.success

    @property
    def command(self) -> str:
        '''The command that was executed.'''
        return self._command

    @property
    def stdout_lines(self) -> list[str]:
        '''Stdout split into lines (strips trailing newline).'''
        return self.stdout.rstrip('\n').split('\n') if self.stdout else []

    @property
    def stderr_lines(self) -> list[str]:
        '''Stderr split into lines (strips trailing newline).'''
        return self.stderr.rstrip('\n').split('\n') if self.stderr else []

    def check_returncode(self) -> None:
        '''
        Raise ExecError if the process failed.

        Raises
        ------
        ExecError
            If returncode is non-zero.
        '''
        if self.failed:
            raise ExecError(
                command=self.command,
                exit_code=self.returncode,
                stdout=self.stdout,
                stderr=self.stderr
            )

    def __repr__(self) -> str:
        return (
            f'ProcessResult(command={self.command!r}, '
            f'returncode={self.returncode}, '
            f'stdout_size={len(self.stdout)}, '
            f'stderr_size={len(self.stderr)})'
        )

    def pipe_to(self, *command: str, **options: Any) -> 'ProcessResult':
        '''
        Pipe stdout to another command.

        Parameters
        ----------
        *command : str
            Command and arguments to pipe to.
        **options : Any
            Additional options passed to run().

        Returns
        -------
        ProcessResult
            Result of the piped command.

        Examples
        --------
        >>> result = run('ls', '-la').pipe_to('grep', 'python')
        >>> result = run('cat', 'file.txt').pipe_to('wc', '-l')
        '''
        if 'input' in options:
            raise ValueError("Cannot specify 'input' when piping")

        return run(*command, input=self.stdout, **options)


def prepare_command(
    command: Sequence[str],
    shell: bool
) -> tuple[str | list[str], str]:
    if shell:
        cmd = ' '.join(command) if len(command) > 1 else command[0]
    else:
        cmd = list(command)
    cmd_str = cmd if isinstance(cmd, str) else shlex.join(cmd)
    return cmd, cmd_str

def prepare_command_context(
    env: Mapping[str, str] | None,
    cwd: StringOrPathlib | None
) -> tuple[Mapping[str, str] | None, str | None]:
    if env is not None:
        process_env = dict(os.environ)
        process_env.update(env)
    else:
        process_env = None
    cwd_str = str(Path(cwd)) if cwd is not None else None
    return process_env, cwd_str

class CommandExecutor:
    """
    Core executor for synchronous commands, encapsulating DRY patterns.
    """

    def __init__(
        self,
        command: Sequence[str] | str,
        cwd: StringOrPathlib | None = None,
        env: Mapping[str, str] | None = None,
        input: str | bytes | None = None,
        timeout: float | None = None,
        capture_output: bool = True,
        check: bool = False,
        shell: bool = False,
        encoding: str = 'utf-8',
        silent: bool = False,
        dry_run: bool = False,
        **kwargs: dict[str, Any]
    ) -> None:
        if not self.command:
            raise InvalidCommandError(command)

        self.command: list[str] = list(command)
        self.cwd: StringOrPathlib | None = cwd
        self.env: Mapping[str, str] | None = env
        self.input: str | bytes | None = input
        self.timeout: float | None = timeout
        self.capture_output: bool = capture_output
        self.check: bool = check
        self.shell: bool = shell
        self.encoding: str = encoding
        self.silent: bool = silent
        self.dry_run: bool = dry_run
        self.subproc_kwargs: dict[str, Any] = kwargs

    @property
    def shell_command(self) -> str:
        if len(self.command) == 1:
            return self.command[0]
        return ' '.join(self.command)

    def command_string(self) -> str:
        """
        Returns the command as a string, suitable for logging.
        If shell=True, it returns a single string command.
        Otherwise, it returns a shell-escaped string.
        """
        if self.shell:
            return self.shell_command
        return shlex.join(self.command)


    def set_environment(self, process_env: Mapping[str, str]) -> None:
        """
        Returns the environment variables for the subprocess.
        If self.env is provided, it merges it with the current environment.
        """
        if not self.env:
            return
        


    def dry_run(self) -> ProcessResult:
        """
        Returns a ProcessResult simulating the command execution without actually running it.
        This is useful for testing or debugging command preparation.
        """
        cmd_str = self.command_string()
        if not self.silent:
            core.debug(f'[DRY RUN] Would execute: {cmd_str}')
        completed = subprocess.CompletedProcess(
            args=self.command,
            returncode=0,
            stdout='',
            stderr=''
        )
        return ProcessResult(
            completed_process=completed,
            command=self.command
        )

    def run(self) -> ProcessResult:


        process_env, cwd_str = self._prepare_context(env, cwd)
        try:
            completed = subprocess.run(
                cmd,
                cwd=cwd_str,
                env=process_env,
                input=input,
                capture_output=capture_output,
                timeout=timeout,
                text=True,
                encoding=encoding,
                shell=shell,
                check=False,
                **kwargs
            )
            result = ProcessResult(
                completed_process=completed,
                command=cmd
            )

            self._log_result(result, silent)
            if check:
                result.check_returncode()

            return result

        except subprocess.TimeoutExpired as e:
            raise TimeoutError(
                f'Command "{cmd_str}" timed out after {timeout} seconds'
            )
        except FileNotFoundError as e:
            raise CommandNotFoundError(
                command=cmd_str,
                message=f'Command not found: {command[0]}'
            ) from e

    def stream(
        self,
        *command: str,
        cwd: StringOrPathlib | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        shell: bool = False,
        encoding: str = 'utf-8',
        silent: bool = False,
        **kwargs: Any
    ) -> Iterator[tuple[str, str]]:
        if not command:
            raise ValueError("At least one command argument is required")
        cmd, cmd_str = self.prepare_command(d, shell)
        if not silent:
            core.debug(f'streaming {cmd_str}')

        process_env, cwd_str = self._prepare_context(env, cwd)
        try:
            with subprocess.Popen(
                cmd,
                cwd=cwd_str,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding=encoding,
                shell=shell,
                **kwargs
            ) as process:
                sel = selectors.DefaultSelector()
                if process.stdout:
                    sel.register(process.stdout, selectors.EVENT_READ, data='stdout')
                if process.stderr:
                    sel.register(process.stderr, selectors.EVENT_READ, data='stderr')

                while process.poll() is None:
                    for key, _ in sel.select(timeout=0.1):
                        stream_name = key.data
                        file_obj = process.stdout if stream_name == 'stdout' else process.stderr
                        if not file_obj:
                            continue
                        if not (line := file_obj.readline()):
                            continue
                        line = line.rstrip('\n')
                        if not silent:
                            core.debug(f'[{stream_name}] {line}')
                        yield (stream_name, line)

                if process.stdout:
                    yield from self._generate_io_stream(
                        process.stdout,
                        silent,
                        'stdout'
                    )
                if process.stderr:
                    yield from self._generate_io_stream(
                        process.stderr,
                        silent,
                        'stderr'
                    )

        except FileNotFoundError as e:
            raise CommandNotFoundError(
                command=cmd_str,
                message=f'Command not found: {command[0]}'
            ) from e

    def _generate_io_stream(
        self,
        proc_io: IO[str],
        silent: bool,
        stream_name: str
    ) -> Iterator[tuple[str, str]]:
        """
        Generator to yield lines from a process IO stream.
        """
        for line in proc_io:
            line = line.rstrip('\n')
            if not silent:
                core.debug(f'[{stream_name}] {line}')
            yield (stream_name, line)

class AsyncCommandExecutor:
    """
    Core executor for asynchronous commands, encapsulating DRY patterns.
    """

    def prepare_command(command: Sequence[str], shell: bool) -> tuple[str | list[str], str]:
        return CommandExecutor().prepare_command(d, shell)

    def _prepare_context(self, env: Mapping[str, str] | None, cwd: StringOrPathlib | None):
        return CommandExecutor()._prepare_context(env, cwd)

    async def run_async(
        self,
        *command: str,
        cwd: StringOrPathlib | None = None,
        env: Mapping[str, str] | None = None,
        input: str | bytes | None = None,
        timeout: float | None = None,
        check: bool = False,
        shell: bool = False,
        encoding: str = 'utf-8',
        silent: bool = False,
        **kwargs: Any
    ) -> ProcessResult:
        if not command:
            raise ValueError("At least one command argument is required")
        cmd, cmd_str = self.prepare_command(d, shell)
        if not silent:
            core.debug(f'Executing async: {cmd_str}')

        process_env, cwd_str = self._prepare_context(env, cwd)
        try:
            create_fn = asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
            proc_args = (cmd,) if shell else tuple(cmd)  # type: ignore
            process = await create_fn(
                *proc_args,
                cwd=cwd_str,
                env=process_env,
                stdin=asyncio.subprocess.PIPE if input else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **kwargs
            )
            input_bytes = input.encode(encoding) if isinstance(input, str) else input
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input_bytes),
                timeout=timeout
            )
            stdout = stdout_bytes.decode(encoding) if stdout_bytes else ''
            stderr = stderr_bytes.decode(encoding) if stderr_bytes else ''

            completed = subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode or 0,
                stdout=stdout,
                stderr=stderr
            )
            result = ProcessResult(completed_process=completed, command=cmd)
            CommandExecutor()._log_result(result, silent)
            if check:
                result.check_returncode()
            return result

        except asyncio.TimeoutError as e:
            process.terminate()
            await process.wait()
            raise CommandTimeoutError(
                command=cmd_str,
                timeout=timeout
            ) from e
        except FileNotFoundError as e:
            raise CommandNotFoundError(
                command=cmd_str,
                message=f'Command not found: {command[0]}'
            ) from e

    async def stream_async(
        self,
        *command: str,
        cwd: StringOrPathlib | None = None,
        env: Mapping[str, str] | None = None,
        shell: bool = False,
        encoding: str = 'utf-8',
        silent: bool = False,
        **kwargs: Any
    ) -> AsyncIterator[tuple[str, str]]:
        if not command:
            raise ValueError("At least one command argument is required")
        cmd, cmd_str = self.prepare_command(d, shell)
        if not silent:
            core.debug(f'Streaming async: {cmd_str}')

        process_env, cwd_str = self._prepare_context(env, cwd)
        try:
            create_fn = asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
            proc_args = (cmd,) if shell else tuple(cmd)  # type: ignore
            process = await create_fn(
                *proc_args,
                cwd=cwd_str,
                env=process_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **kwargs
            )

            async def read_stream(stream, name):
                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode(encoding).rstrip('\n')
                    if not silent:
                        core.debug(f'[{name}] {line}')
                    yield (name, line)

            readers = [read_stream(process.stdout, 'stdout'), read_stream(process.stderr, 'stderr')]
            async for item in self._merge_async_iterators(*readers):
                yield item
            await process.wait()

        except FileNotFoundError as e:
            raise CommandNotFoundError(
                command=cmd_str,
                message=f'Command not found: {command[0]}'
            ) from e

    async def _merge_async_iterators(self, *iterators):
        tasks = {asyncio.create_task(self._anext_safe(it)): it for it in iterators}
        while tasks:
            done, _ = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                result = task.result()
                if result is not None:
                    yield result
                    it = tasks.pop(task)
                    tasks[asyncio.create_task(self._anext_safe(it))] = it
                else:
                    tasks.pop(task)

    async def _anext_safe(self, iterator):
        try:
            return await iterator.__anext__()
        except StopAsyncIteration:
            return None


# Singleton instances
_sync_executor = CommandExecutor()
_async_executor = AsyncCommandExecutor()

# Module-level API unchanged

def run(*args: Any, **kwargs: Any) -> ProcessResult:
    return _sync_executor.run(*args, **kwargs)


def stream(*args: Any, **kwargs: Any) -> Iterator[tuple[str, str]]:
    return _sync_executor.stream(*args, **kwargs)


async def run_async(*args: Any, **kwargs: Any) -> ProcessResult:
    return await _async_executor.run_async(*args, **kwargs)


async def stream_async(*args: Any, **kwargs: Any) -> AsyncIterator[tuple[str, str]]:
    return _async_executor.stream_async(*args, **kwargs)


def shell(command: str, *, check: bool = True, capture_output: bool = True, **kwargs: Any) -> ProcessResult:
    return run(command, shell=True, check=check, capture_output=capture_output, **kwargs)


def output(*command: str, strip: bool = True, **kwargs: Any) -> str:
    result = run(*command, check=True, **kwargs)
    return result.stdout.strip() if strip else result.stdout


def check_output(*command: str, **kwargs: Any) -> str:
    return run(*command, check=True, **kwargs).stdout


def pipeline(*commands: Sequence[str], **kwargs: Any) -> ProcessResult:
    if not commands:
        raise ValueError("At least one command is required")
    result = run(*commands[0], **kwargs)
    for cmd in commands[1:]:
        result = result.pipe_to(*cmd, **kwargs)
    return result


@contextlib.contextmanager

def cd(path: StringOrPathlib) -> Generator[None, None, None]:
    old_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


@contextlib.contextmanager

def environment(**env_vars: str) -> Generator[None, None, None]:
    old_env = {}
    for key, value in env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
