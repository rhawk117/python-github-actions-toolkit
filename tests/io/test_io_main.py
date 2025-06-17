import platform
import time
from pathlib import Path

import pytest

import action_toolkit.io as aio

OS_WIN = platform.system() == "Windows"
OS_POSIX = not OS_WIN


def forge_structure(root: Path) -> None:
    '''creates a mixed hierarchy: nested dirs, files, binary, and a symlink.'''
    (root / "dir1").mkdir()
    (root / "dir1" / "file1.txt").write_text("hello")
    (root / "dir2").mkdir()
    (root / "file2.bin").write_bytes(b"\x00\x01")
    (root / "empty").mkdir()
    sy = root / "link"
    sy.symlink_to(root / "dir1" / "file1.txt")


def make_executable(path: Path) -> Path:
    """
    On POSIX: write a shell header & chmod +x
    On Windows: create .bat extension
    Returns the actual file path used.
    """
    if OS_POSIX:
        path.chmod(0o755)
        return path
    else:
        bat = path.with_suffix(".bat")
        bat.write_text("@echo off")
        return bat


class TestCopy:
    def test_copy_file_to_new(self, tmp_path: Path):
        src = tmp_path / "a.txt"
        dst = tmp_path / "sub" / "b.txt"
        src.write_text("A")
        out = aio.copy(src, dst)
        assert out.samefile(dst)
        assert dst.read_text() == "A"

    def test_copy_dir_into_new(self, tmp_path: Path):
        src = tmp_path / "d1"
        (src / "x").mkdir(parents=True, exist_ok=True)
        (src / "x" / "f.txt").write_text("f")
        dest_dir = tmp_path / "dest"
        out = aio.copy(src, dest_dir)
        assert (dest_dir / "x" / "f.txt").read_text() == "f"

    def test_copy_dir_into_existing_dir_merges(self, tmp_path: Path):
        src = tmp_path / "s"
        (src / "a.txt").write_text("1")
        dst = tmp_path / "d"
        dst.mkdir()
        extra = dst / "b.txt"
        extra.write_text("2")
        out = aio.copy(src, dst)
        assert (dst / "a.txt").read_text() == "1"
        assert extra.read_text() == "2"

    def test_copy_remove_existing_file_before_copy(self, tmp_path: Path):
        src = tmp_path / "f"
        dst = tmp_path / "g"
        src.write_text("new")
        dst.write_text("old")
        aio.copy(src, dst)
        assert dst.read_text() == "new"

    def test_copy_file_overwrite_false_keeps(self, tmp_path: Path):
        src, dst = tmp_path / "a", tmp_path / "b"
        src.write_text("new")
        dst.write_text("old")
        ret = aio.copy(src, dst, overwrite=False)
        assert ret.samefile(dst)
        assert dst.read_text() == "old"

    def test_copy_file_to_dir_error(self, tmp_path: Path):
        src = tmp_path / "f"
        src.write_text("x")
        dst = tmp_path / "d"
        dst.mkdir()
        with pytest.raises(aio.ActionIOError):
            aio.copy(src, dst)

    def test_copy_missing_src(self, tmp_path: Path):
        with pytest.raises(aio.ActionIOError):
            aio.copy(tmp_path / "no", tmp_path / "out")


class TestMove:
    def test_move_file_basic(self, tmp_path: Path):
        src, dst = tmp_path / "a", tmp_path / "b"
        src.write_text("1")
        out = aio.move(src, dst)
        assert out.read_text() == "1" and not src.exists()

    def test_move_overwrite_true_removes_existing(self, tmp_path: Path):
        src = tmp_path / "a"
        dst = tmp_path / "b"
        src.write_text("X")
        dst.write_text("Y")
        aio.move(src, dst, overwrite=True)
        assert dst.read_text() == "X"

    def test_move_overwrite_false_error(self, tmp_path: Path):
        src = tmp_path / "a"
        dst = tmp_path / "b"
        src.write_text("X")
        dst.write_text("Y")
        with pytest.raises(aio.ActionIOError):
            aio.move(src, dst, overwrite=False)

    def test_move_dir_to_new_parent(self, tmp_path: Path):
        src = tmp_path / "d"
        src.mkdir()
        (src / "x").write_text("x")
        dst = tmp_path / "sub" / "d"
        out = aio.move(src, dst)
        assert (out / "x").read_text() == "x"

    def test_move_missing_src_error(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            aio.move(tmp_path / "no", tmp_path / "d")


class TestRemove:
    def test_remove_file(self, tmp_path: Path):
        f = tmp_path / "f"
        f.write_text("x")
        aio.remove(f)
        assert not f.exists()

    def test_remove_empty_dir(self, tmp_path: Path):
        d = tmp_path / "d"
        d.mkdir()
        aio.remove(d)
        assert not d.exists()

    def test_remove_nonempty_dir_error(self, tmp_path: Path):
        d = tmp_path / "d"
        (d / "x").mkdir(parents=True)
        with pytest.raises(Exception):
            aio.remove(d)

    def test_remove_nonexistent_force_succeeds(self, tmp_path: Path):
        aio.remove(tmp_path / "no", force=True)

    def test_remove_symlink_only(self, tmp_path: Path):
        f, l = tmp_path / "f", tmp_path / "l"
        f.write_text("x")
        l.symlink_to(f)
        aio.remove(l)
        assert f.exists() and not l.exists()


class TestMkdirP:
    def test_mkdir_new(self, tmp_path: Path):
        p = tmp_path / "a" / "b"
        out = aio.mkdir_p(p)
        assert p.is_dir() and out.samefile(p)

    def test_mkdir_existing_file_error(self, tmp_path: Path):
        f = tmp_path / "f"
        f.write_text("x")
        with pytest.raises(Exception):
            aio.mkdir_p(f)


class TestWhich:
    def test_which_empty_tool(self):
        with pytest.raises(aio.ActionIOError):
            aio.which("")

    @pytest.mark.skipif(OS_POSIX, reason="Windows PATHEXT")
    def test_which_windows_ext(self, tmp_path: Path, monkeypatch):
        exe = tmp_path / "app.exe"
        exe.write_text("x")
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setenv("PATHEXT", ".EXE")
        assert aio.which("app", check=True).lower().endswith(".exe")

    @pytest.mark.skipif(OS_WIN, reason="POSIX exec bits")
    def test_which_posix_exec(self, tmp_path: Path, monkeypatch):
        exe = make_executable(tmp_path / "t")
        monkeypatch.setenv("PATH", str(tmp_path))
        assert aio.which("t", check=True) == str(exe)

    def test_which_notfound(self, monkeypatch):
        monkeypatch.setenv("PATH", "")
        assert aio.which("x") is None
        with pytest.raises(aio.ActionIOError):
            aio.which("x", check=True)


class TestStatFileStat:
    def test_stat_file_properties(self, tmp_path: Path) -> None:
        f = tmp_path / "f"
        f.write_text("0123")
        fs: aio.FileStat = aio.stat(f)
        assert fs.byte_size == 4
        assert fs.is_file and not fs.is_dir, "Should be a file"
        perm_octal = fs.get_perm_octal()
        assert (
            perm_octal.isdigit() and len(perm_octal) == 4
        ), "Should be a 4-digit octal string"
        assert isinstance(fs.mtime, float), "Modification time should be a float"

    def test_stat_symlink(self, tmp_path: Path) -> None:
        f, l = tmp_path / "f", tmp_path / "l"
        f.write_text("x")
        l.symlink_to(f)
        sy_fs = aio.stat(l, follow_symlinks=False)
        assert sy_fs.is_symlink


class TestTouch:
    def test_touch_creates_and_updates(self, tmp_path: Path):
        p = tmp_path / "t"
        aio.touch(p)
        t1 = p.stat().st_mtime
        time.sleep(0.01)
        aio.touch(p)
        t2 = p.stat().st_mtime
        assert t2 >= t1


class TestWalkFast:
    def test_walk_all(self, tmp_path: Path) -> None:
        forge_structure(tmp_path)
        got = set(aio.walk_fast(tmp_path))
        expect = {
            tmp_path,
            tmp_path / "dir1",
            tmp_path / "dir1" / "file1.txt",
            tmp_path / "dir2",
            tmp_path / "file2.bin",
            tmp_path / "empty",
            tmp_path / "link",
        }
        assert expect <= got, f"Expected {expect} but got {got}"

    def test_walk_follow(self, tmp_path: Path) -> None:
        forge_structure(tmp_path)
        got = set(aio.walk_fast(tmp_path, follow_symlinks=True))
        assert (
            tmp_path / "link" / "file1.txt"
        ) in got, "Should follow symlink to file1.txt"


class TestReadWrite:
    def test_read_write_basic(self, tmp_path: Path):
        p = tmp_path / "x"
        aio.write(p, "h")
        assert aio.read(p) == "h"

    def test_write_append_and_create(self, tmp_path: Path):
        p = tmp_path / "y"
        aio.write(p, "a")
        aio.write(p, "b", append=True)
        assert aio.read(p) == "ab"

    def test_read_missing_error(self):
        with pytest.raises(FileNotFoundError):
            aio.read("no")


class TestSplitExtMulti:
    @pytest.mark.parametrize(
        "fname,levels,exp",
        [
            ("a.tar.gz", 2, ".tar.gz"),
            ("b.gz", 1, ".gz"),
            ("c", 2, ""),
            ("d.tar.bz2.xz", 3, ".tar.bz2.xz"),
        ],
    )
    def test_split(self, fname, levels, exp):
        stem, suf = aio.split_extmulti(fname, levels=levels)
        assert suf == exp and fname.startswith(
            stem
        ), f"Split failed for {fname} with levels={levels}"


class TestRelpathSafe:
    def test_same_folder(self, tmp_path: Path) -> None:
        f = tmp_path / "a"
        f.mkdir()
        assert aio.relpath_safe(f, start=tmp_path) == Path("a"), "Should return relative path in same folder"

    def test_diff_drive_windows(self, tmp_path: Path):
        if OS_WIN:
            other = Path("C:/") if tmp_path.drive != "C:" else Path("D:/")
            assert aio.relpath_safe(tmp_path, start=other).is_absolute()
        else:
            pytest.skip("POSIX will always return relative")


class TestUniquePath:
    def test_basic(self, tmp_path: Path) -> None:
        f = tmp_path / "file"
        f.write_text("x")
        u = aio.unique_path(f)
        assert u != f and not u.exists(), 'A unique path should\'ve been created'


    def test_limit_exceeded(self, tmp_path: Path):
        base = tmp_path / "l"
        base.write_text("x")
        for i in range(1, 4):
            (tmp_path / f"l_{i}").write_text("x")
        with pytest.raises(aio.ActionIOError):
            aio.unique_path(base, limit=3)


class TestChmodPerm:
    @pytest.mark.skipif(OS_WIN, reason="POSIX only")
    def test_octal_valid(self, tmp_path: Path):
        f = tmp_path / "p"
        f.write_text("")
        aio.chmod_perm(f, "600")
        assert (f.stat().st_mode & 0o777) == 0o600

    @pytest.mark.skipif(OS_WIN, reason="POSIX only")
    def test_symbolic_valid(self, tmp_path: Path):
        f = tmp_path / "p2"
        f.write_text("")
        aio.chmod_perm(f, "rwx------")
        assert (f.stat().st_mode & 0o777) == 0o700

    def test_octal_invalid(self, tmp_path: Path):
        f = tmp_path / "p3"
        f.write_text("")
        with pytest.raises(ValueError):
            aio.chmod_perm(f, "999")


class TestEnvHelpers:
    def test_iter_env_path_strip(self, monkeypatch):
        monkeypatch.setenv("PATH", " /a ; /b ; ; ")
        out = [p for p in aio.iter_env_path()]
        assert out == [Path("/a"), Path("/b")]

    def test_get_pathext_default(self, monkeypatch):
        monkeypatch.delenv("PATHEXT", False)
        assert aio.get_pathext_extensions() == []

    @pytest.mark.skipif(OS_POSIX, reason="Windows only")
    def test_get_pathext_custom(self, monkeypatch):
        monkeypatch.setenv("PATHEXT", ".X;.Y")
        assert aio.get_pathext_extensions() == [".X", ".Y"]


class TestExecBit:
    @pytest.mark.skipif(OS_WIN, reason="POSIX only")
    def test_exec_true(self, tmp_path: Path):
        f = tmp_path / "e"
        make_executable(f)
        assert aio.is_unix_executable(f.stat())

    @pytest.mark.skipif(OS_WIN, reason="POSIX only")
    def test_exec_false(self, tmp_path: Path):
        f = tmp_path / "e2"
        f.write_text("")
        f.chmod(0o644)
        assert not aio.is_unix_executable(f.stat())


class TestAtomicWrite:
    def test_atomic_write_text_and_binary(self, tmp_path: Path):
        f = tmp_path / "a"
        aio.atomic_write(f, "hi")
        assert f.read_text() == "hi"
        aio.atomic_write(f, b"hi2", mode="wb")
        assert f.read_bytes() == b"hi2"

    def test_atomic_write_in_tmp_dir_and_parent(self, tmp_path: Path):
        td = tmp_path / "td"
        td.mkdir()
        f = tmp_path / "c" / "x"
        aio.atomic_write(f, "z", tmp_dir=td)
        assert f.read_text() == "z" and not any(td.iterdir())


def test_all_exported():
    public = {name for name in dir(aio) if not name.startswith("_")}
    assert set(aio.__all__) <= public
