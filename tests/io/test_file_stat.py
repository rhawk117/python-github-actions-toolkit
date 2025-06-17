# tests/test_file_stat.py
"""
Comprehensive pytest suite for `action_toolkit.io.internals.file_stat.FileStat`.
Covers all public methods, edge cases, symlink handling, permission formatting,
user/group resolution, and fallback behavior.
"""

import os
import stat
import pwd
import grp
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from action_toolkit.io import FileStat

IS_WIN = platform.system() == "Windows"


class TestFileStatFromPath:
    def test_path_file_basic(self, tmp_path: Path):
        f = tmp_path / "a.txt"
        f.write_text("hello")
        fs = FileStat.path(f)
        st = fs.get()
        assert isinstance(st, os.stat_result)
        assert fs.byte_size == st.st_size == 5
        for attr in ("mtime", "atime"):
            dt = getattr(fs, attr)
            assert isinstance(dt, datetime)
            assert dt.tzinfo is timezone.utc
            assert abs(dt.timestamp() - getattr(st, f"st_{attr}")) < 0.001
        if hasattr(st, "st_birthtime"):
            ct = fs.ctime
            assert isinstance(ct, datetime)
            assert ct.tzinfo is timezone.utc
            assert abs(ct.timestamp() - st.st_birthtime) < 0.001
        else:
            pytest.skip("st_birthtime not supported on this platform")

    def test_path_directory(self, tmp_path: Path):
        d = tmp_path / "d"
        d.mkdir()
        fs = FileStat.path(d)
        assert fs.is_dir()
        assert not fs.is_file()
        raw_mode = fs.get().st_mode & 0o777
        assert int(fs.get_perm_octal(), 8) == raw_mode
        s = fs.permission_str()
        assert len(s) == 9 and all(c in "rwx-" for c in s)

    @pytest.mark.skipif(IS_WIN, reason="symlinks require elevated Windows privileges")
    def test_path_symlink_follow_and_nofollow(self, tmp_path: Path):
        d = tmp_path / "d"
        d.mkdir()
        (d / "x.txt").write_text("data")
        link = tmp_path / "link"
        link.symlink_to(d / "x.txt")
        fs_f = FileStat.path(link, follow_symlinks=True)
        assert fs_f.is_file()
        assert not fs_f.is_symlink()
        fs_n = FileStat.path(link, follow_symlinks=False)
        assert fs_n.is_symlink()
        assert not fs_n.is_file()

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            FileStat.path("/no/such/file")


class TestFileStatFromFd:
    def test_fd_with_path(self, tmp_path: Path):
        f = tmp_path / "b.txt"
        f.write_text("xyz")
        with open(f, "rb") as fh:
            fs = FileStat.fd(fh.fileno(), path=f)
        assert fs.byte_size == 3
        assert f.as_posix() in str(fs)

    def test_fd_without_path(self, tmp_path: Path):
        f = tmp_path / "c.bin"
        f.write_bytes(b"\0" * 10)
        with open(f, "rb") as fh:
            fs = FileStat.fd(fh.fileno())
        assert fs.byte_size == 10
        s = str(fs)
        assert s.endswith(">") and "." not in s.split()[-1]


class TestSizeHuman:
    @pytest.mark.parametrize(
        "size,expected",
        [
            (0, "0 B"),
            (500, "500 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1024 * 1024, "1.0 MB"),
            (3 * 1024 * 1024 + 512 * 1024, "3.5 MB"),
        ],
    )
    def test_size_human(self, tmp_path: Path, size: int, expected: str):
        f = tmp_path / "s.bin"
        f.write_bytes(b"\0" * size)
        fs = FileStat.path(f)
        assert fs.size_human() == expected


class TestPermissions:
    @pytest.mark.skipif(IS_WIN, reason="permission bits unreliable on Windows")
    def test_get_perm_octal_and_str(self, tmp_path: Path):
        f = tmp_path / "perm.txt"
        f.write_text("x")
        f.chmod(0o640)
        fs = FileStat.path(f)
        octal = fs.get_perm_octal()
        assert octal.startswith("0o")
        assert int(octal, 8) == fs.get().st_mode & 0o777
        rstr = fs.permission_str()
        expected = "".join(
            c if (fs.get().st_mode & bit) else "-"
            for bit, c in [
                (stat.S_IRUSR, "r"),
                (stat.S_IWUSR, "w"),
                (stat.S_IXUSR, "x"),
                (stat.S_IRGRP, "r"),
                (stat.S_IWGRP, "w"),
                (stat.S_IXGRP, "x"),
                (stat.S_IROTH, "r"),
                (stat.S_IWOTH, "w"),
                (stat.S_IXOTH, "x"),
            ]
        )
        assert rstr == expected


class TestOwnerGroup:
    @pytest.mark.skipif(IS_WIN, reason="owner/group not applicable on Windows")
    def test_owner_group_resolution(self, tmp_path: Path):
        f = tmp_path / "o.txt"
        f.write_text("o")
        fs = FileStat.path(f)
        uid = fs.uid
        gid = fs.gid
        # Should match system resolution
        assert fs.owner == pwd.getpwuid(uid).pw_name # type: ignore[attr-defined]
        assert fs.group == grp.getgrgid(gid).gr_name # type: ignore[attr-defined]

    def test_owner_group_fallback(self, tmp_path: Path, monkeypatch):
        f = tmp_path / "o2.txt"
        f.write_text("o2")
        fs = FileStat.path(f)
        monkeypatch.setattr(
            "action_toolkit.io.internals.file_stat.pwd.getpwuid",
            lambda uid: (_ for _ in ()).throw(KeyError()),
        )
        assert fs.owner == str(fs.uid)
        monkeypatch.setattr(
            "action_toolkit.io.internals.file_stat.grp.getgrgid",
            lambda gid: (_ for _ in ()).throw(KeyError()),
        )
        assert fs.group == str(fs.gid)


class TestStrRepr:
    def test_str_contains_components(self, tmp_path: Path):
        f = tmp_path / "z.txt"
        f.write_text("zz")
        fs = FileStat.path(f)
        s = str(fs)
        assert s.startswith("<file ")
        assert f.name in s
        assert f.as_posix() in s
        assert s.endswith(">"), "String repr must end with '>'"


class TestGetMethod:
    def test_get_returns_stat(self, tmp_path: Path):
        f = tmp_path / "g.txt"
        f.write_text("yy")
        fs = FileStat.path(f)
        st = fs.get()
        assert isinstance(st, os.stat_result)
        assert st.st_size == 2


class TestInvalidFd:
    def test_fd_invalid_descriptor(self):
        with pytest.raises(OSError):
            FileStat.fd(-999)
