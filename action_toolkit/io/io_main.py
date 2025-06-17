'''
**io.io.py**
File system operations for GitHub Actions.

This module provides cross-platform file operations including copy, move,
delete, and executable finding functionality.
'''

from __future__ import annotations
import os
from pathlib import Path
import shutil
import time
import warnings

from action_toolkit.core.path_utils import StringOrPathlib
from action_toolkit.io.internals.file_stat import FileStat

from . import fs_utils
from .internals.exceptions import ActionIOError


def exists(path: str) -> bool:
    return Path(path).exists()


def cp(
    *,
    source: str | Path,
    dest: str | Path,
    recursive: bool = False,
    force: bool = True,
    copy_src_dir: bool = True,
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
    recursive : bool, optional
        Whether to copy directories recursively, by default False
    force : bool, optional
        Whether to overwrite existing files, by default True
    copy_src_dir : bool, optional
        Whether to copy source directory into destination, by default True

    Raises
    ------
    ActionIOError
        If source doesn't exist or recursive copy attempted without recursive flag.

    Examples
    --------
    >>> # Copy a file
    >>> cp(source='file.txt', dest='backup.txt')

    >>> # Copy directory recursively
    >>> cp(source='src_dir', dest='dest_dir', recursive=True)

    >>> # Copy without overwriting
    >>> cp(source='file.txt', dest='existing.txt', force=False)
    '''

    src = Path(source).resolve()
    dst = Path(dest).resolve()

    if not src.exists():
        raise ActionIOError(f'no such file or directory: {source}')

    if dst.exists():
        if dst.is_file() and not force:
            return

        if dst.is_dir() and src.is_dir() and copy_src_dir:
            dst = dst / src.name

    if src.is_dir():
        if not recursive:
            raise ActionIOError(
                f'Failed to copy. {source} is a directory, but tried to copy without recursive flag.'
            )
        copy_dir_recursive(
            src=src,
            dest=dst,
            force=force
        )
        return

    if dst.exists() and src.samefile(dst):
        raise ActionIOError(f"'{dst}' and '{src}' are the same file")

    copyfile(
        src=src,
        dest=dst,
        force=force
    )


def mv(
    source: str | Path,
    dest: str | Path,
    *,
    force: bool = True
) -> None:
    '''
    Move a file or directory.

    Parameters
    ----------
    source : Union[str, Path]
        Source path to move from.
    dest : Union[str, Path]
        Destination path to move to.
    force : bool, optional
        Whether to overwrite existing files, by default True

    Raises
    ------
    ActionIOError
        If source doesn't exist or destination exists and force=False.
    '''

    src = Path(source).resolve()
    dst = Path(dest).resolve()

    if not src.exists():
        raise ActionIOError(f'no such file or directory: {source}')

    dst_exists = dst.exists()
    if dst_exists and dst.is_dir():
        dst = dst / src.name
        dst_exists = dst.exists()  # Re-check after adjusting path

    if dst_exists:
        if not force:
            raise ActionIOError(
                f'cannot move {source} to {dest}. Destination already exists.'
            )
        rm_rf(path=dst)  # remove destination if it exists first

    mkdir_p(path=dst.parent)  # ensure parent directory exists

    try:
        src.rename(dst)
    except OSError as e:
        raise ActionIOError(
            f'could not move {source} to {dest}',
            cause=e
        ) from e


def rm_rf(path: str | Path) -> None:
    '''
    Remove a path recursively with force.

    Parameters
    ----------
    path : Union[str, Path]
        Path to remove.

    Raises
    ------
    ActionIOError
        If path contains invalid characters on Windows or removal fails.

    Examples
    --------
    >>> # Remove a file
    >>> rm_rf(path='temp.txt')

    >>> # Remove a directory and all contents
    >>> rm_rf(path='temp_dir')
    '''
    fp = Path(path).resolve()
    path_str = str(path)

    if fs_utils.IS_WINDOWS and any(char in path_str for char in '*"<>|'):
        raise ActionIOError(
            f'Invalid characters in path: {path_str}. '
            'Windows does not allow these characters in file or directory names.'
        )

    if not fp.exists():
        return

    try:
        if fp.is_dir():
            shutil.rmtree(fp, ignore_errors=True)
        else:
            fp.unlink(missing_ok=True)
    except OSError as e:
        raise ActionIOError(
            f'could not remove {path_str}',
            cause=e
        ) from e


def mkdir_p(path: StringOrPathlib) -> None:
    '''
    Make a directory. Creates the full path with folders in between.

    Parameters
    ----------
    path : Union[str, Path]
        Path to create.

    Raises
    ------
    ActionIOError
        If path is empty or creation fails.

    Examples
    --------
    >>> # Create nested directories
    >>> mkdir_p(path='path/to/nested/dir')
    '''
    if not path:
        raise ActionIOError("parameter 'path' is required")

    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ActionIOError(
            f'could not create directory {path}',
            cause=e
        ) from e


def which(tool: str, *, check: bool = False) -> str:
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
    ActionIOError
        If tool parameter is empty.
    ActionIOError
        If check=True and tool is not found.

    Examples
    --------
    >>> # Find python executable
    >>> python_path = which(tool='python')

    >>> # Check that git exists
    >>> git_path = which(tool='git', check=True)
    '''
    if not tool:
        raise ActionIOError("parameter 'tool' is required")

    if check:
        result = which(tool=tool, check=False)
        if not result:
            platform_msg = (
                "Please verify the file path exists or can be found in PATH. "
                "Also verify the file has a valid executable extension."
                if fs_utils.IS_WINDOWS else
                "Please verify the file path exists or can be found in PATH. "
                "Also check the file is executable."
            )
            raise ActionIOError(f"Unable to locate executable: {tool}. {platform_msg}")
        return result

    matches = find_in_path(tool=tool)
    return matches[0] if matches else ''


def find_in_path(*, tool: str) -> list[str]:
    '''
    Returns a list of all occurrences of the given tool on the system path.

    Parameters
    ----------
    tool : str
        Name of the tool to find.

    Returns
    -------
    list[str]
        List of paths where the tool was found.

    Raises
    ------
    ActionIOError
        If tool parameter is empty.

    Examples
    --------
    >>> # Find all python installations
    >>> pythons = find_in_path(tool='python')
    '''
    if not tool:
        raise ActionIOError("parameter 'tool' is required")

    extensions = fs_utils.get_pathext_extensions() if fs_utils.IS_WINDOWS else []

    if fs_utils.is_rooted(tool):
        exec_path = fs_utils.try_get_executable(tool, extensions=extensions)
        return [exec_path] if exec_path else []

    if os.sep in tool or (fs_utils.IS_WINDOWS and '/' in tool):
        return []

    matches = []
    for directory in fs_utils.iter_path_dirs():
        inferred_path = Path(directory) / tool
        exec_path = fs_utils.try_get_executable(
            inferred_path,
            extensions=extensions
        )
        if exec_path:
            matches.append(exec_path)
    return matches


def rm(
    path: str | Path,
    *,
    force: bool = False,
    max_retries: int = 1,
    recursive: bool = False,
    retry_delay: float = 0.0
) -> None:
    '''
    Remove a file or directory with retry logic.

    Parameters
    ----------
    path : Union[str, Path]
        Path to remove.
    force : bool, optional
        Whether to ignore errors, by default False
    max_retries : int, optional
        Maximum number of retry attempts, by default 1
    recursive : bool, optional
        Whether to remove directories recursively, by default False
    retry_delay : float, optional
        Delay between retries in seconds, by default 0.0

    Raises
    ------
    ActionIOError
        If removal fails and force=False
    '''
    path_obj = Path(path)

    for attempt in range(max_retries):
        try:
            if recursive and path_obj.is_dir():
                shutil.rmtree(str(path_obj), ignore_errors=force)
            else:
                path_obj.unlink(missing_ok=force)
            break
        except Exception as e:
            if not force and attempt == max_retries - 1:
                raise ActionIOError(f"Failed to remove {path}: {e}") from e
            if retry_delay > 0 and attempt < max_retries - 1:
                time.sleep(retry_delay)


def copyfile(
    *,
    src: Path,
    dest: Path,
    force: bool = False,
) -> None:
    '''
    Copy a single file, handling symlinks appropriately.

    Parameters
    ----------
    src : Path
        Source file path
    dest : Path
        Destination file path
    force : bool, optional
        Whether to overwrite existing files, by default False
    '''
    dest.parent.mkdir(parents=True, exist_ok=True)

    if src.is_symlink():
        if dest.exists():
            dest.unlink(missing_ok=True)

        target = src.readlink()
        dest.symlink_to(target)

    elif not dest.exists() or force:
        shutil.copy2(src, dest)


def copy_dir_recursive(
    *,
    src: Path,
    dest: Path,
    force: bool = False,
    max_depth: int = 255,
    current_depth: int = 0
) -> None:
    '''
    Recursively copy a directory and its contents to a new location.

    Parameters
    ----------
    src : Path
        Source directory path
    dest : Path
        Destination directory path
    force : bool, optional
        Whether to forcefully copy (overwrite), by default False
    max_depth : int, optional
        Maximum recursion depth, by default 255
    current_depth : int, optional
        Current recursive depth, by default 0
    '''
    if current_depth > max_depth:
        return

    dest.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            copy_dir_recursive(
                src=item,
                dest=target,
                force=force,
                max_depth=max_depth,
                current_depth=current_depth + 1
            )
        else:
            copyfile(src=item, dest=target, force=force)

    try:
        shutil.copystat(src, dest)
    except OSError:
        warnings.warn(
            f"Could not copy file stat from '{src}' to '{dest}'.",
            RuntimeWarning,
            stacklevel=2
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


def stat(path: str | Path, *, follow_symlinks: bool = True) -> FileStat:
    '''
    Get file stat, returns a FileStat object wrapping os.stat_result.

    Parameters
    ----------
    path : Union[str, Path]
        Path to stat.
    follow_symlinks : bool, optional
        Whether to follow symbolic links, by default True

    Returns
    -------
    FileStat
        File status information wrapper.
    '''
    return FileStat.path(path, follow_symlinks=follow_symlinks)


def touch(
    file_path: StringOrPathlib,
    *,
    create_parents: bool = True,
    exist_ok: bool = True
) -> None:
    '''
    Creates an empty file or updates its timestamp (like touch command).

    Parameters
    ----------
    file_path : StringOrPathlib
        Path to the file to touch
    create_parents : bool, optional
        Create parent directories if they don't exist, by default True
    exist_ok : bool, optional
        Don't raise error if file already exists, by default True

    Raises
    ------
    ActionIOError
        If file creation fails or file exists and exist_ok=False
    '''
    path = Path(file_path)

    if path.exists():
        if not exist_ok:
            raise ActionIOError(f"File already exists: {file_path}")
        path.touch(exist_ok=True)
        return

    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)

    try:
        path.touch(exist_ok=exist_ok)
    except OSError as e:
        raise ActionIOError(f"Failed to create file '{file_path}'", cause=e) from e

def join(*paths: str) -> Path:
    '''
    explicit join function for pathlib.Path

    Parameters
    ----------
    *paths : StringOrPathlib
        Path components to join.

    Returns
    -------
    Path
        Joined path as a Path object.
    '''
    return Path(*(p for p in paths))

def read(
    *parts: str,
    encoding: str = 'utf-8',
    errors: str = 'strict',
    strip_trailing_newline: bool = False
) -> str:
    '''
    Reads and return the contents of a file.

    Parameters
    ----------
    *parts: str
        The file path parts to concatenate, like `os.path.join`.
    encoding : str, optional
        Text encoding to use, by default 'utf-8'
    errors : str, optional
        How to handle encoding errors, by default 'strict'
    strip_trailing_newline : bool, optional
        Whether to strip trailing newline from output, by default False

    Returns
    -------
    str
        The file contents

    Raises
    ------
    ActionIOError
        If no files provided or file cannot be read

    Examples
    --------
    >>> # Read a file
    >>> content = read('path', 'to', 'file.txt')
    >>> print(content)
    '''
    path = os.path.join(*parts)

    if not path or not os.path.exists(path):
        raise ActionIOError(f'No files provided or file does not exist: {path}')

    try:
        with open(path, 'r', encoding=encoding, errors=errors) as file:
            result = file.read()
    except OSError as e:
        raise ActionIOError(f'Error reading file {path}: {e}') from e

    if strip_trailing_newline and result.endswith('\n'):
        result = result.rstrip('\n')

    return result

