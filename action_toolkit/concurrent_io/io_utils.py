'''
**io.io_util**
Low-level file system utilities for the IO toolkit that are non-blocking,
awaitable and platform-agnostic.
'''

from __future__ import annotations

import os
import sys
import stat as stat_module
import asyncio
import warnings
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final
from .async_fs import async_fs
from ..corelib.types import FilePath

_fs = AsyncFileSystem()


IS_WINDOWS: Final[bool] = sys.platform == 'win32'


async def chmod(path: FilePath, mode: int) -> None:
    """Change file mode bits."""
    return await _fs.chmod(path, mode)


async def copyfile(
    *,
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str]
) -> str:
    """Copy file src to dst and return dst."""
    return await _fs.copyfile(src, dst)


async def lstat(path: FilePath) -> os.stat_result:
    '''Like stat(), but doesn't follow symbolic links.

    Args:
        path (FilePath): _the file path_

    Returns:
        os.stat_result: _the result_
    '''
    return await _fs.lstat(path)


async def readdir(path: FilePath) -> list[str]:
    """Return a list containing the names of the files in the directory."""
    return await _fs.readdir(path)


async def readlink(path: FilePath) -> str:
    """Return the path to which the symbolic link points."""
    return await _fs.readlink(path)


async def rename(*, src: FilePath, dst: FilePath) -> None:
    """Rename a file or directory."""
    return await _fs.rename(src, dst)


async def stat(path: FilePath) -> os.stat_result:
    """Get the status of a file or a file descriptor."""
    return await _fs.stat(path)


async def unlink(path: FilePath) -> None:
    """Remove a file."""
    return await _fs.unlink(path)


async def run_in_executor(
    func: Callable[..., Any],
    *args: object,
    **kwargs: object
) -> asyncio.Future[Any]:
    '''
    Runs a function in the asyncio event loop's executor.

    Args:
        func (Callable[..., Any]): _the function to run_

    Returns:
        asyncio.Future[Any]: _the result of the function call_
    '''
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


async def mkdir(path: Path | str, *, recursive: bool = False) -> None:
    '''
    Create a directory.

    Parameters
    ----------
    path : Union[Path, str]
        Directory path to create.
    recursive : bool
        Whether to create parent directories.
    '''
    path = Path(path)
    await run_in_executor(
        path.mkdir,
        0o777,  # default mode for directories
        True,
        recursive
    )


async def symlink(
    *,
    src: Path | str,
    dst: Path | str,
    target_is_directory: bool = False
) -> None:
    '''
    Create a symbolic link.

    Parameters
    ----------
    src : Union[Path, str]
        Source path (target of the link).
    dst : Union[Path, str]
        Destination path (the link itself).
    target_is_directory : bool
        Whether the target is a directory (Windows only).
    '''
    await run_in_executor(
        os.symlink,
        str(src),
        str(dst),
        target_is_directory
    )


async def rm(
    path: Path | str,
    *,
    force: bool = False,
    max_retries: int = 1,
    recursive: bool = False,
    retry_delay: float = 0.0
) -> None:
    '''
    Remove a file or directory.

    Parameters
    ----------
    path : Union[Path, str]
        Path to remove.
    force : bool
        Whether to ignore errors.
    max_retries : int
        Maximum number of retry attempts.
    recursive : bool
        Whether to remove directories recursively.
    retry_delay : float
        Delay between retries in seconds.
    '''
    path = Path(path)

    for attempt in range(max_retries):
        try:
            if recursive and path.is_dir():
                await run_in_executor(shutil.rmtree, str(path), force)
            else:
                await run_in_executor(path.unlink, True)
            break
        except Exception as e:
            if not force and attempt == max_retries - 1:
                raise
            if retry_delay > 0 and attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)


async def exists(path: Path | str) -> bool:
    '''
    Check if a path exists.

    Parameters
    ----------
    path : Union[Path, str]
        Path to check.

    Returns
    -------
    bool
        True if path exists, False otherwise.
    '''
    try:
        await stat(path)
        return True
    except OSError as err:
        if err.errno == 2:  # ENOENT
            return False
        raise


async def is_directory(
    path: Path | str,
    use_stat: bool = False
) -> bool:
    '''
    Check if path is a directory.

    Parameters
    ----------
    path : Union[Path, str]
        Path to check.
    use_stat : bool
        Whether to use stat instead of lstat (follows symlinks).

    Returns
    -------
    bool
        True if path is a directory.
    '''
    stats = await (stat if use_stat else lstat)(path)
    return stat_module.S_ISDIR(stats.st_mode)


def is_rooted(p: str) -> bool:
    '''
    Check if a path is rooted (absolute).

    On OSX/Linux, true if path starts with '/'. On Windows, true for paths like:
    \\, \\hello, \\\\hello\\share, C:, and C:\\hello (and corresponding alternate separator cases).

    Parameters
    ----------
    p : str
        Path to check.

    Returns
    -------
    bool
        True if path is rooted/absolute.

    Raises
    ------
    ValueError
        If path is empty.
    '''
    p = normalize_separators(p)
    if not p:
        raise ValueError('is_rooted() parameter "p" cannot be empty or null')

    if IS_WINDOWS:
        return (
            p.startswith('\\') or  # e.g. \ or \hello or \\hello
            (len(p) > 2 and p[1:3] == ':\\')  # e.g. C: or C:\hello
        )

    return p.startswith('/')


def _try_get_exc_warning(
    file_path: str,
    err: Exception | OSError
) -> str:
    '''
    Generate a warning message for an OSError.

    Parameters
    ----------
    file_path : str
        File path that caused the error.
    err : OSError
        The OSError that occurred.

    Returns
    -------
    str
        Warning message.
    '''
    return (
        'Unexpected error occured while attempting to determine '
        f'if an executable file exists \'{file_path}\': {err}'
    )


async def try_get_executable_path(
    file_path: str,
    *,
    extensions: list[str]
) -> str:
    '''
    Best effort attempt to determine whether a file exists and is executable.

    Parameters
    ----------
    file_path : str
        File path to check.
    extensions : list[str]
        Additional file extensions to try.

    Returns
    -------
    str
        File path if exists and is executable, otherwise empty string.
    '''
    stats: Optional[os.stat_result] = None

    try:
        stats = await stat(file_path)
    except OSError as err:
        if err.errno != 2:  # ENOENT, file does not exist
            warnings.warn(
                _try_get_exc_warning(file_path, err),
                RuntimeWarning
            )

    if stats and stat_module.S_ISREG(stats.st_mode):
        if IS_WINDOWS:
            upper_ext = Path(file_path).suffix.upper()
            if any(valid_ext.upper() == upper_ext for valid_ext in extensions):
                return file_path
        else:
            if is_unix_executable(stats):
                return file_path

    original_file_path = file_path
    for extension in extensions:
        file_path = original_file_path + extension

        stats = None
        try:
            stats = await stat(file_path)
        except OSError as err:
            if err.errno != 2:  # ENOENT, file does not exist
                warnings.warn(
                    _try_get_exc_warning(file_path, err),
                    RuntimeWarning
                )

        if stats and stat_module.S_ISREG(stats.st_mode):
            if IS_WINDOWS:
                try:
                    directory = os.path.dirname(file_path)
                    upper_name = os.path.basename(file_path).upper()
                    for actual_name in await readdir(directory):
                        if upper_name == actual_name.upper():
                            file_path = os.path.join(directory, actual_name)
                            break
                except Exception as err:
                    warnings.warn(
                        _try_get_exc_warning(file_path, err),
                        RuntimeWarning
                    )

                return file_path
            else:
                if is_unix_executable(stats):
                    return file_path

    return ''


def normalize_separators(p: str) -> str:
    '''
    Normalize path separators.

    Parameters
    ----------
    p : str
        Path to normalize.

    Returns
    -------
    str
        Normalized path.
    '''
    p = p or ''
    if IS_WINDOWS:
        p = p.replace('/', '\\')

        return os.path.normpath(p)

    return os.path.normpath(p)


def is_unix_executable(stats: os.stat_result) -> bool:
    '''
    Check if file is executable on Unix, I have no clue
    what the fancy bits are (lol)

    Parameters
    ----------
    stats : os.stat_result
        File stats.

    Returns
    -------
    bool
        True if file is executable.
    '''
    return (
        (stats.st_mode & 0o001) > 0 or
        ((stats.st_mode & 0o010) > 0 and
         hasattr(os, 'getgid') and
         hasattr(stats, 'st_gid') and
         stats.st_gid == os.getgid()) or
        ((stats.st_mode & 0o100) > 0 and
         hasattr(os, 'getuid') and
         hasattr(stats, 'st_uid') and
         stats.st_uid == os.getuid())
    )


def get_cmd_path() -> str:
    '''
    Get the path of cmd.exe in windows.

    Returns
    -------
    str
        Path to cmd.exe or 'cmd.exe' if COMSPEC not set.
    '''
    return os.environ.get('COMSPEC', 'cmd.exe')
