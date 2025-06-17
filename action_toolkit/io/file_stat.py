'''
**action_toolkit.io.internals.file_stat**
Wrapper around `os.stat_result` to provide additional convenience methods
'''
import dataclasses
import os
import stat
import pwd
import grp
from datetime import datetime, timezone
from pathlib import Path
from typing import Self

from action_toolkit.corelib.types.io import StringOrPathlib


@dataclasses.dataclass(frozen=True, slots=True)
class FileStat:
    '''
    A result object for `os.stat_result` with additional convenience methods.
    '''
    _result: os.stat_result
    _path: Path | None = dataclasses.field(default=None, repr=False, hash=False)


    @classmethod
    def path(
        cls,
        path: StringOrPathlib,
        *,
        follow_symlinks: bool = True,
    ) -> Self:
        '''Create a FileStat instance from a file path.

        Parameters
        ----------
        path : StringOrPathlib
            _the string or pathlib_
        follow_symlinks : bool, optional
            _whether to follow symlinks_, by default True

        Returns
        -------
        Self
            _the cls instance_
        '''
        p = Path(path)
        stat_result = os.stat(
            p,
            follow_symlinks=follow_symlinks
        )
        return cls(_result=stat_result, _path=p)

    @classmethod
    def fd(
        cls,
        fd: int,
        *,
        path: StringOrPathlib | None = None,
    ) -> Self:
        '''
        Creates a FileStat instance from a file descriptor.

        Parameters
        ----------
        fd : int
            _the file descriptor_
        path : StringOrPathlib | None, optional
            _string or pathlib.Path_, by default None

        Returns
        -------
        Self
            _the cls instance_
        '''
        stat_result = os.fstat(fd)
        p = Path(path) if path else None
        return cls(_result=stat_result, _path=p)

    @property
    def byte_size(self) -> int:
        '''File size in bytes'''
        return self._result.st_size


    def size_human(self) -> str:
        '''Convert file size to a human-readable format.

        Returns
        -------
        str
            _human readable string_
        '''
        size = float(self.byte_size)
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if size < 1024:
                return f'{size:,.1f} {unit}' if unit != 'B' else f'{int(size)} B'
            size /= 1024
        return f'{size:,.1f} EB'

    def _dt(self, ts: float) -> datetime:
        '''Convert to datetime in UTC'''
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    @property
    def mtime(self) -> datetime:
        '''Last modified time as datetime in UTC'''
        return self._dt(self._result.st_mtime)

    @property
    def atime(self) -> datetime:
        '''Last access time as datetime in UTC'''
        return self._dt(self._result.st_atime)

    @property
    def ctime(self) -> datetime:
        '''Creation time as datetime in UTC'''
        return self._dt(self._result.st_birthtime)

    def is_file(self) -> bool:
        '''Check if path is a file, uses `stat.S_ISREG`'''
        return stat.S_ISREG(self._result.st_mode)

    def is_dir(self) -> bool:
        '''Check if path is a directory, uses ``stat.S_ISDIR``'''
        return stat.S_ISDIR(self._result.st_mode)

    def is_symlink(self) -> bool:
        '''Check if path is a symbolic link, uses `stat.S_ISLNK`'''
        return stat.S_ISLNK(self._result.st_mode)

    def get_perm_octal(self) -> str:
        '''Get file permissions as octal string'''
        return oct(self._result.st_mode & 0o777)

    def permission_str(self) -> str:
        '''Get file permissions as a string like 'rwxr-xr-x' '''
        triples = [
            (stat.S_IRUSR, 'r'), (stat.S_IWUSR, 'w'), (stat.S_IXUSR, 'x'),
            (stat.S_IRGRP, 'r'), (stat.S_IWGRP, 'w'), (stat.S_IXGRP, 'x'),
            (stat.S_IROTH, 'r'), (stat.S_IWOTH, 'w'), (stat.S_IXOTH, 'x'),
        ]
        return ''.join(c if self._result.st_mode & b else '-' for b, c in triples)

    @property
    def uid(self) -> int:
        '''User ID of the file owner, equivalent to `st_uid`'''
        return self._result.st_uid

    @property
    def gid(self) -> int:
        '''Group ID of the file owner, equivalent to `st_gid`'''
        return self._result.st_gid

    @property
    def owner(self) -> str:
        '''Owner username of the file, uses `pwd.getpwuid` to resolve UID'''
        try:
            return pwd.getpwuid(self.uid).pw_name # type: ignore[no-untyped-call]
        except (KeyError, AttributeError):
            return str(self.uid)

    @property
    def group(self) -> str:
        '''Group name of the file, uses `grp.getgrgid` to resolve GID'''
        try:
            return grp.getgrgid(self.gid).gr_name # type: ignore[no-untyped-call]
        except (KeyError, AttributeError):
            return str(self.gid)

    def get(self) -> os.stat_result:
        '''Return the underlying computed os.stat_result object'''
        return self._result

    def __str__(self) -> str:
        '''String representation of the FileStat instance.

        Returns
        -------
        str
            _the string representation_
        '''
        kind = 'dir' if self.is_dir else 'link' if self.is_symlink else 'file'
        owner = f'{self.owner}:{self.group}'
        return f'<{kind} {self.permission_str()} {owner} {self.size_human} ' \
               f'{self._path or ""}>'