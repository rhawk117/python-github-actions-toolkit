# action_toolkit/io.py
from __future__ import annotations
import os
import shutil
import stat as _stat
from pathlib import Path
from collections.abc import Generator, Iterator
import tempfile
from typing import Literal


from action_toolkit.corelib.types.io import StringOrPathlib
from .exceptions import ActionIOError
from .file_stat import FileStat


__all__ = [
    'copy',
    'move',
    'remove',
    'mkdir_p',
    'which',
    'stat',
    'touch',
    'walk_fast',
    'read',
    'write',
    'split_extmulti',
    'relpath_safe',
    'unique_path',
    'chmod_perm',
    'get_pathext_extensions',
    'iter_env_path',
    'is_unix_executable',
    'atomic_write',
    'FileStat',
    'ActionIOError'
]


def copy(src: StringOrPathlib, dst: StringOrPathlib, *, overwrite: bool = True) -> Path:
    """Copy file or directory; returns destination path."""
    src_p, dst_p = map(Path, (src, dst))
    if not src_p.exists():
        raise ActionIOError(f"No such file or directory: {src}")

    if dst_p.exists():
        if not overwrite:
            return dst_p

        if dst_p.is_dir() and src_p.is_file():
            raise ActionIOError("refusing to overwrite, the destination is a directory and the source is a file")

        if dst_p.is_file():
            dst_p.unlink()

    dst_p.parent.mkdir(parents=True, exist_ok=True)

    if src_p.is_dir():
        shutil.copytree(src_p, dst_p, dirs_exist_ok=True)
    else:
        shutil.copy2(src_p, dst_p)
    return dst_p


def move(src: StringOrPathlib, dst: StringOrPathlib, *, overwrite: bool = True) -> Path:
    '''
    Moves a file or directory from *src* to *dst*.

    Parameters
    ----------
    src : StringOrPathlib
        _the source path to move_
    dst : StringOrPathlib
        _the destination_
    overwrite : bool, optional
        _whether to overwrite existing files at the destination_, by default True

    Returns
    -------
    Path
        _the moved path_

    Raises
    ------
    FileNotFoundError
        _the src does not exist_
    ActionIOError
        _when the destination exists and overwrite is false_
    '''
    src_p, dst_p = map(Path, (src, dst))
    if not src_p.exists():
        raise FileNotFoundError(f"cannot move, no such file or directory {src}")

    if dst_p.exists():
        if not overwrite:
            raise ActionIOError(f"destination path exists and overwrite was set to false. {dst}")

        remove(dst_p, recursive=True, force=True)

    dst_p.parent.mkdir(parents=True, exist_ok=True)
    return Path(shutil.move(src_p, dst_p))


def remove(
    path: StringOrPathlib,
    *,
    recursive: bool = False,
    force: bool = False
) -> None:
    '''
    Remove a file or directory at *path*. If *recursive* is True,
    removes directories recursively.

    Parameters
    ----------
    path : StringOrPathlib
        _the path_
    recursive : bool, optional
        _whether to remove recursively_, by default False
    force : bool, optional
        _whether to forcefully remove_, by default False

    Raises
    ------
    ActionIOError
        _an error occurs and not force_
    '''
    p = Path(path)
    try:
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p) if recursive else p.rmdir()
        else:
            p.unlink()
    except FileNotFoundError:
        if not force:
            raise
    except OSError as e:
        if not force:
            raise ActionIOError(str(e)) from e


def mkdir_p(path: StringOrPathlib) -> Path:
    '''
    Create a directory at *path*, including any necessary parent directories
    equivalent to `mkdir -p` in Unix or
    `Path(path).mkdir(parents=True, exist_ok=True)` in Python.

    Parameters
    ----------
    path : StringOrPathlib
        _description_

    Returns
    -------
    Path
        _description_
    '''
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def which(tool: str, *, check: bool = False) -> str | None:
    '''
    Locate an executable in the system's PATH using `shutil.which`.

    Parameters
    ----------
    tool : str
        _the name of the tool_
    check : bool, optional
        _raises if no result is found_, by default False

    Returns
    -------
    str | None
        _the result if check is true_

    Raises
    ------
    ActionIOError
        _tool is nullish or check is true and the tool is not found_
    '''
    if not tool:
        raise ActionIOError('parameter "tool" is required')

    result = shutil.which(tool)
    if check and not result:
        raise ActionIOError(f"unable to locate executable: {tool}")
    return result


def stat(path: StringOrPathlib, *, follow_symlinks: bool = True) -> FileStat:
    '''
    Returns a convience wrapper around `os.stat` that returns a `FileStat` object.

    Parameters
    ----------
    path : StringOrPathlib
        _the path_
    follow_symlinks : bool, optional
        _whether to follow symlinks_, by default True

    Returns
    -------
    FileStat
        _the file stat instance_
    '''
    return FileStat.path(
        path,
        follow_symlinks=follow_symlinks
    )


def touch(path: StringOrPathlib) -> None:
    '''
    Similar to `touch` command in Unix, creates an empty file if it does not exist.

    Parameters
    ----------
    path : StringOrPathlib
        _the string or path_
    '''
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)

def walk_fast(
    root: StringOrPathlib,
    *,
    follow_symlinks: bool = False
) -> Iterator[Path]:
    '''
    Yield all files & dirs under *root* using :pyfunc:`os.scandir` for speed.

    Notes
    -----
    * Significantly faster than :pyfunc:`pathlib.Path.rglob` on large trees.
    '''
    stack: list[Path] = [Path(root)]
    while stack:
        current = stack.pop()
        yield current
        if not current.is_dir():
            continue
        with os.scandir(current) as it:
            for entry in it:
                try:
                    path = Path(entry.path)
                    if entry.is_symlink() and not follow_symlinks:
                        continue
                    stack.append(path)
                except OSError:
                    continue


def read(path: StringOrPathlib, *, encoding="utf-8") -> str:
    '''equivalent to `Path(path).read_text(encoding=encoding)`.

    Parameters
    ----------
    path : StringOrPathlib
        _the path_
    encoding : str, optional
        _the encoding_, by default "utf-8"

    Returns
    -------
    str
        _the string that was read_
    '''
    return Path(path).read_text(encoding=encoding)


def write(
    path: StringOrPathlib,
    content: str,
    *,
    append: bool = False,
    encoding: str = "utf-8"
) -> None:
    mode = "a" if append else "w"
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if mode == 'a' and not p.exists():
        p.write_text(content, encoding=encoding)
    else:
        p.write_text(p.read_text(encoding) + content, encoding=encoding)


def split_extmulti(path: StringOrPathlib, *, levels: int = 2) -> tuple[str, str]:
    """
    Split a path into base and extension, supporting multiple extensions.

    Parameters
    ----------
    path : StringOrPathlib
        The file path to split.
    levels : int, optional
        Number of extension levels to consider, by default 2.

    Returns
    -------
    tuple[str, str]
        A tuple containing the base name and the extension(s).
    """
    p = Path(path)
    suffixes = ''.join(p.suffixes[-levels:])
    stem = p.as_posix()[:-len(suffixes)] if suffixes else p.as_posix()
    return stem, suffixes

def relpath_safe(path: StringOrPathlib, start: StringOrPathlib = '.') -> Path:
    '''
    Like :pyfunc:`os.path.relpath`, but falls back to absolute path if the
    relative path cannot be computed (e.g. different drives on Windows).
    '''
    try:
        return Path(os.path.relpath(path, start))
    except ValueError:
        return Path(path).resolve()


def unique_path(path: StringOrPathlib, *, sep: str = '_', limit: int = 100) -> Path:
    '''
    Attempts to create a unique file path by appending a suffix

    Examples
    --------
    >>> unique_path('log.txt')  # 'log.txt' or 'log_1.txt'
    '''
    p = Path(path)
    if not p.exists():
        return p

    stem, suf = p.stem, p.suffix
    result = None
    for i in range(1, limit + 1):
        candidate = p.with_name(f'{stem}{sep}{i}{suf}')
        if not candidate.exists():
            result = candidate
            break

    if result is None:
        raise ActionIOError(f"Unable to find a unique path for {path} after {limit} attempts")

    return result

def chmod_perm(path: StringOrPathlib, perm: str) -> None:
    """
    Allows for setting permissions in both symbolic or octal notation.

    Parameters
    ----------
    path : StringOrPathlib
        The file or directory path.
    mode : int
        The permission mode to set (e.g., 0o755).

    Examples
    --------
    >>> chmod_perm('example.txt', '644')  # Sets permissions to -rw-r--r--
    >>> chmod_perm('example.sh', 'rwxr-xr-x')  # Sets permissions to -rwxr-xr-x
    """
    p = Path(path)
    if perm.isdigit():
        mode = int(perm, 8)
        os.chmod(p, mode)
        return
    flags = (
        (_stat.S_IRUSR, 'r'), (_stat.S_IWUSR, 'w'), (_stat.S_IXUSR, 'x'),
        (_stat.S_IRGRP, 'r'), (_stat.S_IWGRP, 'w'), (_stat.S_IXGRP, 'x'),
        (_stat.S_IROTH, 'r'), (_stat.S_IWOTH, 'w'), (_stat.S_IXOTH, 'x'),
    )
    mode = 0
    for bit, ch in flags:
        if not ch in perm[:len(flags)]:
            continue
        idx = perm.index(ch)
        if perm[idx] != '-':
            mode |= bit

    os.chmod(p, mode)

def get_pathext_extensions() -> list[str]:
    '''Gets the PATHEXT environment variable extensions.

    Returns
    -------
    list[str]
        _the pathext environment variable_
    '''
    pathext = os.environ.get('PATHEXT', '')
    if not pathext:
        return []

    return [ext for ext in pathext.split(os.pathsep) if ext]

def iter_env_path() -> Generator[Path, None, None]:
    '''Iterate over directories in the PATH environment variable.

    Yields
    ------
    Generator[str, None, None]
        _the path environment variables_
    '''
    path_env = os.environ.get('PATH', '')
    if not path_env:
        return

    for directory in path_env.split(os.pathsep):
        yield Path(directory)


def is_unix_executable(stats: os.stat_result) -> bool:
    '''Check if file has executable permissions on Unix systems.'''
    return bool(stats.st_mode & (_stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH))

def atomic_write(
    path: StringOrPathlib,
    data: str | bytes,
    *,
    mode: Literal['w', 'wb'] = 'w',
    encoding: str = 'utf-8',
    tmp_dir: StringOrPathlib | None = None
) -> Path:
    '''
    Write *data* atomically: the target file is replaced only after the
    contents are safely written and flushed.

    Parameters
    ----------
    path
        Destination file.
    data
        ``str`` or ``bytes`` buffer.
    mode
        ``'w'`` or ``'wb'`` style mode matching *data* type.
    encoding
        Text encoding when *data* is ``str``.
    tmp_dir
        Directory for the temporary file; defaults to ``Path(path).parent``.

    Returns
    -------
    Path
        Final path.
    '''
    dst = Path(path)
    tmp_dir = Path(tmp_dir) if tmp_dir else dst.parent
    fd, tmp_name = tempfile.mkstemp(dir=tmp_dir, prefix=f'.{dst.name}.')
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, mode, encoding=encoding) as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, dst)
    finally:
        tmp_path.unlink(missing_ok=True)
    return dst.resolve()
