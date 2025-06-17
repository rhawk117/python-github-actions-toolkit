'''Tests for core.path_utils module'''

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from action_toolkit.core.path_utils import (
    to_posix_path,
    to_win32_path,
    to_platform_path,
    normalize_path,
    is_absolute,
    get_relative_path
)


class TestToPosixPath:
    '''Test cases for to_posix_path function'''
    @pytest.mark.parametrize(
        'input_path, expected_output',
        [
            ('C:\\Users\\test\\file.txt', 'C:/Users/test/file.txt'),
            ('D:\\Projects\\MyApp\\src', 'D:/Projects/MyApp/src'),
            ('\\\\server\\share\\file', '//server/share/file'),
        ]
    )
    def test_windows_to_posix(self, input_path, expected_output):
        '''Test converting Windows paths to POSIX'''
        assert to_posix_path(input_path) == expected_output

    @pytest.mark.parametrize(
        "const_path",
        [
            '/home/user/file.txt',
            '/usr/local/bin',
            './relative/path',
        ]
    )
    def test_posix_unchanged(self, const_path):
        '''Test POSIX paths remain unchanged'''
        assert to_posix_path(const_path) == const_path

    def test_mixed_separators(self):
        '''Test paths with mixed separators'''
        assert to_posix_path(
            'C:\\Users/test\\file.txt') == 'C:/Users/test/file.txt'
        assert to_posix_path('/home\\user/documents') == '/home/user/documents'

    def test_path_object(self):
        '''Test with Path object input'''
        path = Path('test') / 'file.txt'
        result = to_posix_path(path)
        assert '/' in result or result == 'test/file.txt'
        assert '\\' not in result

    def test_empty_path(self):
        '''Test empty path'''
        assert to_posix_path('') == ''

    @pytest.mark.parametrize(
        "input_path, expected_output",
        [
            ('.', '.'),
            ('..', '..'),
            ('\\', '/'),
            ('\\\\', '//'),
        ]
    )
    def test_special_cases(self, input_path, expected_output):
        '''Test special path cases'''
        assert to_posix_path(
            input_path) == expected_output, f"Failed for {input_path}"


class TestToWin32Path:
    '''Test cases for to_win32_path function'''

    def test_posix_to_windows(self):
        '''Test converting POSIX paths to Windows'''
        assert to_win32_path('/home/user/file.txt') == '\\home\\user\\file.txt'
        assert to_win32_path('/usr/local/bin') == '\\usr\\local\\bin'
        assert to_win32_path('./relative/path') == '.\\relative\\path'

    def test_windows_unchanged(self):
        '''Test Windows paths remain in Windows format'''
        assert to_win32_path(
            'C:\\Users\\test\\file.txt') == 'C:\\Users\\test\\file.txt'
        assert to_win32_path('D:\\Projects\\MyApp') == 'D:\\Projects\\MyApp'

    def test_mixed_separators_normalized(self):
        '''Test mixed separators are normalized to Windows'''
        assert to_win32_path(
            'C:/Users\\test/file.txt') == 'C:\\Users\\test\\file.txt'
        assert to_win32_path(
            '/home\\user/documents') == '\\home\\user\\documents'

    def test_path_object(self):
        '''Test with Path object input'''
        path = Path('test') / 'file.txt'
        result = to_win32_path(path)
        assert '\\' in result or result == 'test\\file.txt'
        assert '/' not in result

    def test_empty_path(self):
        '''Test empty path'''
        assert to_win32_path('') == ''

    def test_special_cases(self):
        '''Test special path cases'''
        assert to_win32_path('.') == '.'
        assert to_win32_path('..') == '..'
        assert to_win32_path('/') == '\\'
        assert to_win32_path('//') == '\\\\'


class TestToPlatformPath:
    '''Test cases for to_platform_path function'''

    @patch('sys.platform', 'win32')
    def test_windows_platform(self):
        '''Test platform path on Windows'''
        assert to_platform_path(
            '/home/user/file.txt') == '\\home\\user\\file.txt'
        assert to_platform_path('C:\\Users\\test') == 'C:\\Users\\test'

    @patch('sys.platform', 'linux')
    def test_linux_platform(self):
        '''Test platform path on Linux'''
        assert to_platform_path(
            'C:\\Users\\test\\file.txt') == 'C:/Users/test/file.txt'
        assert to_platform_path('/home/user') == '/home/user'

    @patch('sys.platform', 'darwin')
    def test_macos_platform(self):
        '''Test platform path on macOS'''
        assert to_platform_path('C:\\Users\\test') == 'C:/Users/test'
        assert to_platform_path('/Users/test') == '/Users/test'

    def test_path_object_preserves_platform(self):
        '''Test Path objects already use platform separators'''
        path = Path('test/file.txt')
        result = to_platform_path(path)
        assert result == str(path)

    def test_current_platform(self):
        '''Test on current platform'''
        if sys.platform.startswith('win'):
            assert '\\' in to_platform_path('test/file.txt')
        else:
            assert '/' in to_platform_path('test\\file.txt')


class TestNormalizePath:
    '''Test cases for normalize_path function'''

    def test_relative_to_absolute(self):
        '''Test converting relative to absolute paths'''
        result = normalize_path('.')
        assert is_absolute(result)
        assert Path(result).is_absolute()

    def test_resolve_components(self):
        '''Test resolving . and .. components'''
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / 'test'
            test_dir.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(test_dir)

                result = normalize_path('../test/./file.txt')
                assert result.endswith(os.path.join('test', 'file.txt'))
                assert '..' not in result
                assert '.' not in Path(result).parts
            finally:
                os.chdir(original_cwd)

    def test_expand_user(self):
        '''Test expanding ~ to home directory'''
        result = normalize_path('~/documents')
        assert result.startswith(str(Path.home()))
        assert '~' not in result

    def test_already_absolute(self):
        '''Test already absolute paths'''
        if sys.platform.startswith('win'):
            path = 'C:\\Windows\\System32'
        else:
            path = '/usr/local/bin'

        result = normalize_path(path)
        assert is_absolute(result)

    def test_non_existent_path(self):
        '''Test normalizing non-existent paths'''
        result = normalize_path('./non/existent/path')
        assert is_absolute(result)
        assert 'non' in result and 'existent' in result and 'path' in result

    def test_empty_path(self):
        '''Test empty path normalizes to current directory'''
        result = normalize_path('')
        expected = str(Path('').absolute())
        assert result == expected


class TestIsAbsolute:
    '''Test cases for is_absolute function'''

    def test_absolute_paths(self):
        '''Test detecting absolute paths'''
        if sys.platform.startswith('win'):
            assert is_absolute('C:\\Users\\test') is True
            assert is_absolute('D:\\') is True
            assert is_absolute('\\\\server\\share') is True
        else:
            assert is_absolute('/home/user') is True
            assert is_absolute('/') is True
            assert is_absolute('/usr/local/bin') is True

    @pytest.mark.parametrize(
        "path",
        [
            'relative/path',
            './file.txt',
            '../parent',
            'file.txt',
            '.',
            '..'
        ]
    )
    def test_relative_paths(self, path):
        '''Test detecting relative paths'''
        assert is_absolute(path) is False, f"Failed for relative path: {path}"

    def test_empty_path(self):
        '''Test empty path is relative'''
        assert is_absolute('') is False


class TestGetRelativePath:
    '''Test cases for get_relative_path function'''

    def test_basic_relative_path(self):
        '''Test basic relative path calculation'''
        assert get_relative_path(
            'C:\\Users\\test\\file.txt', 'C:\\Users') == os.path.join(
                'test', 'file.txt')

    def test_same_path(self):
        '''Test relative path when paths are the same'''
        path = '/home/user/test' if not sys.platform.startswith(
            'win') else 'C:\\Users\\test'
        assert get_relative_path(path, path) == '.'

    def test_path_objects(self):
        '''Test with Path objects'''
        base = Path('/home/user')
        target = Path('/home/user/documents/file.txt')

        result = get_relative_path(target, base)
        assert result == os.path.join('documents', 'file.txt')

    def test_different_drives_windows(self):
        '''Test paths on different drives on Windows'''
        if sys.platform.startswith('win'):
            result = get_relative_path('D:\\folder\\file.txt', 'C:\\Users')
            assert result.startswith('D:')

    def test_unrelated_paths(self):
        '''Test completely unrelated paths'''
        if not sys.platform.startswith('win'):
            result = get_relative_path('/usr/local/bin', '/home/user')
            assert result == os.path.join('..', '..', 'usr', 'local', 'bin')

    def test_with_dots(self):
        '''Test paths containing . and ..'''
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / 'base'
            base.mkdir()

            target = base / '..' / 'base' / 'file.txt'
            result = get_relative_path(str(target), str(base))

            assert result == os.path.join(
                '..', 'base', 'file.txt'), f"Failed for {target} relative to {base}"
