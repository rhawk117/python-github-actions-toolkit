'''
**io.fs_utils**

Concise low-level file system utilities wrapper for
`pathlib.Path`, `os`, `shutil` and `stat`

This module provides synchronous file system operations and platform-specific utilities.
'''

from __future__ import annotations
from collections.abc import Generator, Sequence
import os
import sys
import stat
import warnings
from pathlib import Path

from action_toolkit.core.path_utils import StringOrPathlib
from action_toolkit.io.internals.exceptions import ActionIOError

IS_WINDOWS = sys.platform == 'win32'

def pathlib_join(*paths: StringOrPathlib) -> Path:
    '''
    Join multiple path components into a single Path object.

    Parameters
    ----------
    *paths : StringOrPathlib
        Path components to join.

    Returns
    -------
    Path
        Joined path as a Path object.
    '''
    return Path(*(str(p) for p in paths))



def is_directory(
    path: str | Path,
    use_stat: bool = False
) -> bool:
    '''
    Check if path is a directory.

    Parameters
    ----------
    path : Union[str, Path]
        Path to check.
    use_stat : bool
        Whether to use stat instead of lstat (follows symlinks).

    Returns
    -------
    bool
        True if path is a directory.
    '''
    if not os.path.exists(path):
        raise ActionIOError(f'path does not exist: {path}')

    stats = os.stat(path) if use_stat else os.lstat(path)
    return stat.S_ISDIR(stats.st_mode)


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
        raise ActionIOError('is_rooted() parameter "p" cannot be empty or null')

    if IS_WINDOWS:
        return (
            p.startswith('\\') or  # e.g. \ or \hello or \\hello
            (len(p) > 2 and p[1:3] == ':\\')  # e.g. C: or C:\hello
        )

    return p.startswith('/')

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
    if not p:
        raise ActionIOError('normalize_separators() parameter "p" cannot be empty or null')

    if IS_WINDOWS:
        p = p.replace('/', '\\')

    return os.path.normpath(p)




def is_unix_executable(stats: os.stat_result) -> bool:
    """Check if file has executable permissions on Unix systems."""
    return bool(stats.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

# **********************
#  try_get_executable utils
# ***********************

def _get_file_stats(file_path: Path | str) -> os.stat_result | None:
    """
    Safely retrieve file statistics.

    Args:
        file_path: Path to examine

    Returns:
        File statistics if successful, None if file doesn't exist or on error
    """
    try:
        return file_path.stat() if isinstance(file_path, Path) else os.stat(str(file_path))
    except FileNotFoundError:
        return None
    except OSError as err:
        warnings.warn(
            f"Unexpected error checking file '{file_path}': {err}",
            RuntimeWarning,
            stacklevel=3
        )
        return None

def _has_valid_extension(
    file_path: Path,
    valid_extensions: Sequence[str]
) -> bool:
    """
    Check if file has a valid extension (case-insensitive).

    Args:
        file_path: File path to check
        valid_extensions: Sequence of valid extensions (e.g., ['.exe', '.bat'])

    Returns:
        True if file has valid extension or no extensions specified
    """
    if not valid_extensions:
        return True

    file_suffix = file_path.suffix.lower()
    return any(ext.lower() == file_suffix for ext in valid_extensions)

def _resolve_actual_case(file_path: Path) -> Path:
    """
    Resolve actual filename case on case-insensitive filesystems.

    On Windows, returns the path with the actual case found in the directory.
    This is necessary because we may have constructed paths with appended
    extensions that don't match the actual file case.

    Args:
        file_path: File path to resolve

    Returns:
        Path with correct case, or original path if resolution fails
    """
    try:
        parent = file_path.parent
        target_name = file_path.name.upper()

        for actual_path in parent.iterdir():
            if actual_path.name.upper() == target_name:
                return actual_path

    except OSError as err:
        warnings.warn(
            f"Could not determine actual case for '{file_path}': {err}",
            RuntimeWarning,
            stacklevel=3
        )

    return file_path


def is_executable(
    file_path: Path,
    file_stats: os.stat_result,
    valid_exts: Sequence[str]
) -> bool:
    '''
    Check if a file is executable based on its stats and extension.

    Parameters
    ----------
    file_path : Path
        _the file path_
    file_stats : os.stat_result
        _the stat results_
    valid_exts : Sequence[str]
        _sequence of allowed extensions_

    Returns
    -------
    bool
        _whether it's executable_
    '''
    if not stat.S_ISREG(file_stats.st_mode):
        return False

    if IS_WINDOWS:
        return _has_valid_extension(file_path, valid_exts)

    return is_unix_executable(file_stats)


def try_get_executable(
    file_path: StringOrPathlib,
    *,
    extensions: Sequence[str]
) -> str:
    '''
    Attempts to resolve the executable of the file path, by first
    checking the exact path, then checking for valid extensions
    and on windows, resolving the actual case of the file.

    Parameters
    ----------
    file_path : StringOrPathlib
        _the base file path_
    extensions : Sequence[str] | None, optional
        _the extensions_, by default None

    Returns
    -------
    str
        _the path of the executable_
    '''
    base_path = Path(file_path).resolve() if isinstance(file_path, str) else file_path
    if stats := _get_file_stats(file_path):
        if is_executable(
            Path(file_path),
            stats,
            extensions
        ):
            return str(file_path)

    is_win32 = IS_WINDOWS
    for ext in extensions:
        candiate = base_path.with_name(base_path.name + ext)
        if not (stats := _get_file_stats(candiate)):
            continue

        if not stat.S_ISREG(stats.st_mode):
            continue

        if is_win32:
            candiate = _resolve_actual_case(candiate)
            return str(candiate)

        if is_unix_executable(stats):
            return str(candiate)

    return ''


def get_pathext_extensions() -> list[str]:
    """Get executable extensions from PATHEXT environment variable."""
    pathext = os.environ.get('PATHEXT', '')
    if not pathext:
        return []

    return [ext for ext in pathext.split(os.pathsep) if ext]


def iter_path_dirs() -> Generator[str, None, None]:
    """Get directories from PATH environment variable."""
    path_env = os.environ.get('PATH', '')
    if not path_env:
        return

    for directory in path_env.split(os.pathsep):
        if directory.strip():
            yield directory.strip()


def find_in_path(tool: str) -> list[str]:
    '''
    Find all occurrences of tool in PATH.

    Parameters
    ----------
    tool : str
        _the tool name_

    Returns
    -------
    list[str]
        _the occurences_

    Raises
    ------
    IOError
        _if tool is null / empty string_
    '''
    if not tool:
        raise IOError("Tool parameter is required")

    extensions = get_pathext_extensions() if IS_WINDOWS else []

    if is_rooted(tool):
        executable_path = try_get_executable(tool, extensions=extensions)
        return [executable_path] if executable_path else []

    if os.sep in tool or (IS_WINDOWS and '/' in tool):
        return []

    matches = []

    for directory in iter_path_dirs():
        candidate = Path(directory) / tool
        executable_path = try_get_executable(candidate, extensions=extensions)
        if executable_path:
            matches.append(executable_path)

    return matches


