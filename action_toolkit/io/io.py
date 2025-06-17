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
    copy_src_dir: bool = True
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
    >>> cp(source='file.txt', dest='backup.txt')

    >>> # Copy directory recursively
    >>> cp(
    ...     source='src_dir',
    ...     dest='dest_dir',
    ...     options=CopyOptions(recursive=True)
    ... )

    >>> # Copy without overwriting
    >>> cp(
    ...     source='file.txt',
    ...     dest='existing.txt',
    ...     options=CopyOptions(force=False)
    ... )
    '''

    src = Path(source).resolve()
    dst = Path(dest).resolve()

    if not src.exists():
        raise ActionIOError(f'no such file or directory: {source}')

    if not dst.exists():
        if not dst.exists() and not force:
            return

        if dst.is_dir() and src.is_dir() and copy_src_dir:
            dst = dst / src.name

    if src.is_dir():
        if not recursive:
            raise IOError(
                f'Failed to copy. {source} is a directory, but tried to copy without recursive flag.'
            )
        copy_dir_recursive(
            src=src,
            dest=dst,
            force=force
        )
        return

    if dst.exists() and src.samefile(dst):
        # a file cannot be copied to itself
        raise IOError(f"'{dst}' and '{src}' are the same file")

    copy_file(
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

    src = Path(source).resolve()
    dst = Path(dest).resolve()


    if not src.exists():
        raise ActionIOError(f'no such file or directory: {source}')

    dst_exists = dst.exists()
    if dst_exists and dst.is_dir():
        dst = dst / src.name

    if dst_exists:
        if not force:
            raise ActionIOError(
                f'cannot move {source} to {dest}. Destination already exists.'
            )
        rm_rf(path=dst) # remove destination if it exists first

    mkdir_p(path=dst.parent) # ensure parent directory exists

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
    IOError
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
        raise IOError(
            f'Invalid characters in path: {path_str}. '
            'Windows does not allow these characters in file or directory names.',
            path_str
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
        )


def mkdir_p(path: StringOrPathlib) -> None:
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
    >>> mkdir_p(path='path/to/nested/dir')
    '''
    if not path:
        raise ValueError("parameter 'path' is required")

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
    ValueError
        If tool parameter is empty.
    IOError
        If check=True and tool is not found.

    Examples
    --------
    >>> # Find python executable
    >>> python_path = which(tool='python')

    >>> # Check that git exists
    >>> git_path = which(tool='git', check=True)
    '''
    if not tool:
        raise ValueError("parameter 'tool' is required")

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
            raise IOError(f"Unable to locate executable: {tool}. {platform_msg}")

    matches = find_in_path(tool=tool)
    return str(matches[0]) if matches else ''


def find_in_path(*, tool: str) -> list[str]:
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
    >>> pythons = find_in_path(tool='python')
    '''
    if not tool:
        raise ValueError("parameter 'tool' is required")

    extensions = fs_utils.get_pathext_extensions() if fs_utils.IS_WINDOWS else []

    if fs_utils.is_rooted(tool):
        exec_path = fs_utils.try_get_executable(tool, extensions=extensions)
        return [exec_path] if exec_path else []

    if os.sep in tool or (fs_utils.IS_WINDOWS and '/' in tool):
        return []

    matches = []
    for paths in fs_utils.iter_path_dirs():
        inferred_path = Path(paths) / tool
        exec_path = fs_utils.try_get_executable(
            inferred_path,
            extensions=extensions
        )
        if exec_path:
            matches.append(str(exec_path))
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
    Remove a file or directory.

    Parameters
    ----------
    path : Union[str, Path]
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
                shutil.rmtree(str(path), ignore_errors=force)
            else:
                path.unlink(missing_ok=True)
            break
        except Exception as e:
            if not force and attempt == max_retries - 1:
                raise
            if retry_delay > 0 and attempt < max_retries - 1:
                time.sleep(retry_delay)


def copy_file(
    *,
    src: Path,
    dest: Path,
    force: bool = False,
) -> None:
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
        _the source_
    dest : Path
        _the destination_
    force : bool, optional
        _whether to forcfully copy_, by default False
    max_depth : int, optional
        _max recursion depth_, by default 255
    current_depth : int, optional
        _current recursive depth_, by default 0
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
            copy_file(src=item, dest=target, force=force)

    try:
        shutil.copystat(src, dest)
    except OSError:
        warnings.warn(
            f"Could not copy file stat from '{src}' to '{dest}'.",
            RuntimeWarning,
            stacklevel=2
        )
        pass



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

    Returns
    -------
    os.stat_result
        File status information.
    '''
    return FileStat.path(path, follow_symlinks=follow_symlinks)
