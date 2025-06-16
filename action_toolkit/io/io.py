'''
**io**
File system operations for GitHub Actions.

This module provides cross-platform file operations including copy, move,
delete, and executable finding functionality.
'''

from __future__ import annotations
import os
import sys
import stat
import shutil
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from . import io_utils
from .exceptions import IOError


@dataclass(frozen=True)
class CopyOptions:
    '''
    Options for copy operations.

    Attributes
    ----------
    recursive : bool
        Whether to recursively copy all subdirectories. Defaults to False.
    force : bool  
        Whether to overwrite existing files in the destination. Defaults to True.
    copy_source_directory : bool
        Whether to copy the source directory along with all the files.
        Only takes effect when recursive=True and copying a directory. Default is True.
    '''
    recursive: bool = False
    force: bool = True
    copy_source_directory: bool = True


@dataclass(frozen=True)
class MoveOptions:
    '''
    Options for move operations.

    Attributes
    ----------
    force : bool
        Whether to overwrite existing files in the destination. Defaults to True.
    '''
    force: bool = True


async def cp(
    *,
    source: str | Path,
    dest: str | Path,
    recursive: bool = False,
    force: bool = True,
    copy_source_directory: bool = True,
) -> None:
    '''
    Copy a file or folder.

    Based off of shelljs - https://github.com/shelljs/shelljs/blob/9237f66c52e5daa40458f94f9565e18e8132f5a6/src/cp.js

    Parameters
    ----------
    source : Union[str, Path]
        Source path to copy from.
    dest : Union[str, Path]
        Destination path to copy to.
    options : Optional[CopyOptions]
        Copy options. Defaults to CopyOptions() if not provided.

    Raises
    ------
    IOError
        If source doesn't exist or recursive copy attempted without recursive flag.

    Examples
    --------
    >>> # Copy a file
    >>> await cp(source='file.txt', dest='backup.txt')

    >>> # Copy directory recursively
    >>> await cp(
    ...     source='src_dir',
    ...     dest='dest_dir',
    ...     options=CopyOptions(recursive=True)
    ... )

    >>> # Copy without overwriting
    >>> await cp(
    ...     source='file.txt',
    ...     dest='existing.txt',
    ...     options=CopyOptions(force=False)
    ... )
    '''

    source = Path(source)
    dest = Path(dest)

    dest_stat = await io_utils.stat(dest) if await io_utils.exists(dest) else None

    if dest_stat and dest_stat.is_file() and not force:
        return

    new_dest = dest
    if dest_stat and dest_stat.is_dir() and copy_source_directory:
        new_dest = dest / source.name

    if not await io_utils.exists(source):
        raise IOError(f'no such file or directory: {source}')

    source_stat = await io_utils.stat(source)

    if source_stat.is_dir():
        if not recursive:
            raise IOError(
                f'Failed to copy. {source} is a directory, but tried to copy without recursive flag.'
            )
        else:
            await _cp_dir_recursive(source, new_dest, 0, force)
    else:
        if source.resolve() == new_dest.resolve():
            raise IOError(f"'{new_dest}' and '{source}' are the same file")

        await _copy_file(source, new_dest, force)


async def mv(
    *,
    source: str | Path,
    dest: str | Path,
    force: bool = True
) -> None:
    '''
    Move a path.

    Parameters
    ----------
    source : Union[str, Path]
        Source path to move.
    dest : Union[str, Path]
        Destination path.
    options : Optional[MoveOptions]
        Move options. Defaults to MoveOptions() if not provided.

    Raises
    ------
    IOError
        If destination exists and force is False.

    Examples
    --------
    >>> # Move a file
    >>> await mv(source='old.txt', dest='new.txt')

    >>> # Move without overwriting
    >>> await mv(
    ...     source='file.txt',
    ...     dest='existing.txt', 
    ...     options=MoveOptions(force=False)
    ... )
    '''

    source = Path(source)
    dest = Path(dest)

    if await io_utils.exists(dest):
        dest_exists = True
        if await io_utils.is_directory(dest):
            dest = dest / source.name
            dest_exists = await io_utils.exists(dest)

        if dest_exists:
            if force:
                await rm_rf(path=dest)
            else:
                raise IOError('Destination already exists')

    await mkdir_p(path=dest.parent)
    await io_utils.rename(src=source, dst=dest)


async def rm_rf(*, path: str | Path) -> None:
    '''
    Remove a path recursively with force.

    Parameters
    ----------
    path : Union[str, Path]
        Path to remove.

    Raises
    ------
    IOError
        If path contains invalid characters on Windows or removal fails.

    Examples
    --------
    >>> # Remove a file
    >>> await rm_rf(path='temp.txt')

    >>> # Remove a directory and all contents
    >>> await rm_rf(path='temp_dir')
    '''
    path = Path(path)

    if io_utils.IS_WINDOWS:
        # Check for invalid characters
        # https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
        if any(char in str(path) for char in '*"<>|'):
            raise IOError(
                'File path must not contain `*`, `"`, `<`, `>` or `|` on Windows'
            )

    try:
        # note if path does not exist, error is silent
        await io_utils.rm(
            path,
            force=True,
            max_retries=3,
            recursive=True,
            retry_delay=0.3
        )
    except Exception as err:
        raise IOError(f'File was unable to be removed {err}')


async def mkdir_p(*, path: str | Path) -> None:
    '''
    Make a directory. Creates the full path with folders in between.

    Parameters
    ----------
    path : Union[str, Path]
        Path to create.

    Raises
    ------
    ValueError
        If path is empty.

    Examples
    --------
    >>> # Create nested directories
    >>> await mkdir_p(path='path/to/nested/dir')
    '''
    if not path:
        raise ValueError('a path argument must be provided')

    path = Path(path)
    await io_utils.mkdir(path, recursive=True)


async def which(*, tool: str, check: bool = False) -> str:
    '''
    Returns path of a tool had the tool actually been invoked. Resolves via paths.
    If you check and the tool does not exist, it will throw.

    Parameters
    ----------
    tool : str
        Name of the tool to find.
    check : bool
        Whether to check if tool exists and is executable.

    Returns
    -------
    str
        Path to the tool, or empty string if not found (when check=False).

    Raises
    ------
    ValueError
        If tool parameter is empty.
    IOError
        If check=True and tool is not found.

    Examples
    --------
    >>> # Find python executable
    >>> python_path = await which(tool='python')

    >>> # Check that git exists
    >>> git_path = await which(tool='git', check=True)
    '''
    if not tool:
        raise ValueError("parameter 'tool' is required")

    if check:
        result = await which(tool=tool, check=False)

        if not result:
            if io_utils.IS_WINDOWS:
                raise IOError(
                    f'Unable to locate executable file: {tool}. Please verify either the file path exists '
                    f'or the file can be found within a directory specified by the PATH environment variable. '
                    f'Also verify the file has a valid extension for an executable file.'
                )
            else:
                raise IOError(
                    f'Unable to locate executable file: {tool}. Please verify either the file path exists '
                    f'or the file can be found within a directory specified by the PATH environment variable. '
                    f'Also check the file mode to verify the file is executable.'
                )

        return result

    matches = await find_in_path(tool=tool)

    if matches:
        return str(matches[0])

    return ''


async def find_in_path(*, tool: str) -> list[Path]:
    '''
    Returns a list of all occurrences of the given tool on the system path.

    Parameters
    ----------
    tool : str
        Name of the tool to find.

    Returns
    -------
    list[Path]
        List of paths where the tool was found.

    Raises
    ------
    ValueError
        If tool parameter is empty.

    Examples
    --------
    >>> # Find all python installations
    >>> pythons = await find_in_path(tool='python')
    '''
    if not tool:
        raise ValueError("parameter 'tool' is required")

    # build the list of extensions to try
    extensions: list[str] = []
    if io_utils.IS_WINDOWS and os.environ.get('PATHEXT'):
        for extension in os.environ['PATHEXT'].split(os.pathsep):
            if extension:
                extensions.append(extension)

    # if it's rooted, return it if exists. otherwise return empty.
    if io_utils.is_rooted(tool):
        file_path = await io_utils.try_get_executable_path(
            tool,
            extensions=extensions
        )

        if file_path:
            return [Path(file_path)]

        return []

    # if any path separators, return empty
    if os.sep in tool:
        return []

    # build the list of directories
    #
    # NOTE technically "where" checks the current directory on Windows. From a toolkit perspective,
    # it feels like we should not do this. Checking the current directory seems like more of a use
    # case of a shell, and the which() function exposed by the toolkit should strive for consistency
    # across platforms.
    directories: list[str] = []

    if os.environ.get('PATH'):
        for p in os.environ['PATH'].split(os.pathsep):
            if p:
                directories.append(p)

    # find all matches
    matches: list[Path] = []

    for directory in directories:
        file_path = await io_utils.try_get_executable_path(
            os.path.join(directory, tool),
            extensions=extensions
        )
        if file_path:
            matches.append(Path(file_path))

    return matches


async def _cp_dir_recursive(
    source_dir: Path,
    dest_dir: Path,
    current_depth: int,
    force: bool
) -> None:
    '''Copy directory recursively with depth limit.'''
    if current_depth >= 255:
        return

    current_depth += 1

    await mkdir_p(path=dest_dir)

    files = await io_utils.readdir(source_dir)

    for file_name in files:
        src_file = source_dir / file_name
        dest_file = dest_dir / file_name
        src_file_stat = await io_utils.lstat(src_file)

        if src_file_stat.is_dir():
            await _cp_dir_recursive(src_file, dest_file, current_depth, force)
        else:
            await _copy_file(src_file, dest_file, force)

    # change the mode for the newly created directory
    src_stat = await io_utils.stat(source_dir)
    await io_utils.chmod(dest_dir, src_stat.st_mode)


async def _copy_file(
    src_file: Path,
    dest_file: Path,
    force: bool
) -> None:
    '''Copy a single file, handling symlinks.'''
    src_stat = await io_utils.lstat(src_file)

    if src_stat.is_symlink():
        try:
            await io_utils.lstat(dest_file)
            await io_utils.unlink(dest_file)
        except OSError as e:
            if e.errno == 1:  # EPERM
                await io_utils.chmod(dest_file, 0o666)
                await io_utils.unlink(dest_file)

        symlink_full = await io_utils.readlink(src_file)
        await io_utils.symlink(
            src=symlink_full,
            dst=dest_file,
            target_is_directory=io_utils.IS_WINDOWS
        )
    elif not await io_utils.exists(dest_file) or force:
        await io_utils.copyfile(src=src_file, dst=dest_file)
