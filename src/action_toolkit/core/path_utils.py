'''
**core.path_utils**
Path conversion utilities for GitHub Actions.

This module provides cross-platform path conversion functions that
mirror the path-utils functionality in @actions/core.
'''

from __future__ import annotations
import sys
from pathlib import Path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from action_toolkit.corelib.types.io import StringOrPathlib


def to_posix_path(path: StringOrPathlib) -> str:
    '''
    Convert a path to POSIX format (forward slashes).

    This function mirrors toPosixPath in path-utils.ts. It converts
    Windows-style paths to POSIX format for cross-platform compatibility.

    Parameters
    ----------
    path : StringOrPathlib
        The path to convert.

    Returns
    -------
    str
        The path in POSIX format with forward slashes.

    Examples
    --------
    >>> to_posix_path('C:\\Users\\test\\file.txt')
    'C:/Users/test/file.txt'

    >>> to_posix_path('/home/user/file.txt')
    '/home/user/file.txt'

    >>> to_posix_path(Path.home() / 'documents')
    '/home/user/documents'  # On Unix
    'C:/Users/user/documents'  # On Windows
    '''
    if isinstance(path, Path):
        path = str(path)

    return path.replace('\\', '/')


def to_win32_path(path: StringOrPathlib) -> str:
    '''
    Convert a path to Windows format (backslashes).

    This function mirrors toWin32Path in path-utils.ts. It converts
    POSIX-style paths to Windows format.

    Parameters
    ----------
    path : Union[str, Path]
        The path to convert.

    Returns
    -------
    str
        The path in Windows format with backslashes.

    Examples
    --------
    >>> to_win32_path('/home/user/file.txt')
    '\\home\\user\\file.txt'

    >>> to_win32_path('C:\\Users\\test\\file.txt')
    'C:\\Users\\test\\file.txt'

    >>> to_win32_path('relative/path/file.txt')
    'relative\\path\\file.txt'
    '''
    if isinstance(path, Path):
        path = str(path)

    normalized = path.replace('\\', '/')

    return normalized.replace('/', '\\')


def to_platform_path(path: StringOrPathlib) -> str:
    '''
    Convert a path to the current platform's format.

    This function mirrors toPlatformPath in path-utils.ts. It converts
    paths to use the appropriate separators for the current OS.

    Parameters
    ----------
    path : StringOrPathlib
        The path to convert.

    Returns
    -------
    str
        The path in the current platform's format.

    Examples
    --------
    >>> # On Windows
    >>> to_platform_path('/home/user/file.txt')
    '\\home\\user\\file.txt'

    >>> # On Unix/Linux/macOS
    >>> to_platform_path('C:\\Users\\test\\file.txt')
    'C:/Users/test/file.txt'
    '''
    if isinstance(path, Path):
        return str(path)

    if sys.platform.startswith('win'):
        return to_win32_path(path)
    else:
        return to_posix_path(path)


def normalize_path(path: StringOrPathlib) -> str:
    '''
    Normalize a path for the current platform of the Action runner.

    This is a helper function that normalizes paths by:
    - Resolving '..' and '.' components
    - Converting to absolute path if possible
    - Using platform-appropriate separators

    Parameters
    ----------
    path : Union[str, Path]
        The path to normalize.

    Returns
    -------
    str
        The normalized path.

    Examples
    --------
    >>> normalize_path('./some/../path')
    '/current/dir/path'  # Absolute path with resolved components

    >>> normalize_path('~/documents')
    '/home/user/documents'  # Expanded home directory
    '''
    p = Path(path).expanduser()

    try:
        p = p.resolve()
    except (OSError, RuntimeError):
        p = p.absolute()

    return str(p)


def is_absolute(path: StringOrPathlib) -> bool:
    '''
    Check if a path is absolute.

    Parameters
    ----------
    path : Union[str, Path]
        The path to check.

    Returns
    -------
    bool
        True if the path is absolute, False otherwise.

    Examples
    --------
    >>> is_absolute('/home/user')
    True

    >>> is_absolute('C:\\Users\\test')
    True

    >>> is_absolute('relative/path')
    False
    '''
    return Path(path).is_absolute()


def get_relative_path(
    target: StringOrPathlib,
    base: StringOrPathlib
) -> str:
    '''
    Get the relative path from a target to a base directory.

    Parameters
    ----------
    target : StringOrPathlib
    base : StringOrPathlib

    Returns
    -------
    str
        _relative path_
    '''
    t = Path(target).resolve(strict=False)
    b = Path(base).resolve(strict=False)
    try:
        return str(t.relative_to(b))
    except ValueError:
        anchor = Path(t.anchor)
        parts_after_anchor = t.parts[len(anchor.parts):]
        return Path(*parts_after_anchor).as_posix()