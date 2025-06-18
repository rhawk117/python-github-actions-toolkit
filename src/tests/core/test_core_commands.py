import io
import os
import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from action_toolkit.core.command import (
    set_output,
    set_command_echo,
    set_failed,
    is_debug,
    export_variable,
    set_secret,
    add_path,
    get_state,
    save_state,
    debug,
    notice,
    warning,
    error,
    start_group,
    end_group,
    group
)
from action_toolkit.core.internals.interfaces import WorkflowEnv, AnnotationProperties


class TestSetOutput:
    '''Test cases for set_output function'''

    def test_output_with_file(self):
        '''Test output using file-based approach'''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            with patch.dict(os.environ, {WorkflowEnv.GITHUB_OUTPUT: temp_path}):
                set_output(name='result', value='success')

                with open(temp_path, 'r') as f:
                    content = f.read()

                assert 'result<<ghadelimiter_' in content
                assert 'success' in content
        finally:
            os.unlink(temp_path)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_output_fallback_command(self, mock_stdout):
        '''Test output using command-based fallback'''
        with patch.dict(os.environ, {}, clear=True):
            set_output(name='myoutput', value='myvalue')

            output = mock_stdout.getvalue()
            assert '::set-output name=myoutput::myvalue' in output

    def test_output_complex_values(self):
        '''Test output with complex values'''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            with patch.dict(os.environ, {WorkflowEnv.GITHUB_OUTPUT: temp_path}):
                set_output(name='data', value={'key': 'value', 'num': 42})

                with open(temp_path, 'r') as f:
                    content = f.read()

                assert '{"key":"value","num":42}' in content
        finally:
            os.unlink(temp_path)


class TestSetCommandEcho:
    '''Test cases for set_command_echo function'''

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_enable_echo(self, mock_stdout):
        '''Test enabling command echo'''
        set_command_echo(enabled=True)
        output = mock_stdout.getvalue()
        assert '::echo::on' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_disable_echo(self, mock_stdout):
        '''Test disabling command echo'''
        set_command_echo(enabled=False)
        output = mock_stdout.getvalue()
        assert '::echo::off' in output


class TestSetFailed:
    '''Test cases for set_failed function'''

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_set_failed_with_string(self, mock_stdout):
        '''Test set_failed with string message'''
        with pytest.raises(SystemExit) as exc_info:
            set_failed(message='Action failed')

        assert exc_info.value.code == 1
        output = mock_stdout.getvalue()
        assert '::error::Action failed' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_set_failed_with_exception(self, mock_stdout):
        '''Test set_failed with exception'''
        test_error = ValueError('Invalid value')

        with pytest.raises(SystemExit) as exc_info:
            set_failed(message=test_error)

        assert exc_info.value.code == 1
        output = mock_stdout.getvalue()
        assert '::error::Invalid value' in output


class TestIsDebug:
    '''Test cases for is_debug function'''

    def test_debug_disabled(self) -> None:
        '''Test debug mode disabled by default'''
        with patch.dict(os.environ, {}, clear=True):
            assert is_debug() is False

    def test_debug_enabled(self) -> None:
        '''Test debug mode enabled'''
        with patch.dict(os.environ, {WorkflowEnv.RUNNER_DEBUG: '1'}):
            assert is_debug() is True

    def test_debug_other_values(self):
        '''Test debug mode with other values'''
        with patch.dict(os.environ, {WorkflowEnv.RUNNER_DEBUG: '0'}):
            assert is_debug() is False

        with patch.dict(os.environ, {WorkflowEnv.RUNNER_DEBUG: 'true'}):
            assert is_debug() is False  # Only '1' enables debug


class TestExportVariable:
    '''Test cases for export_variable function'''

    def test_export_with_file(self):
        '''Test export using file-based approach'''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            with patch.dict(os.environ, {WorkflowEnv.GITHUB_ENV: temp_path}):
                export_variable(name='MY_VAR', value='my value')

                assert os.environ['MY_VAR'] == 'my value'

                with open(temp_path, 'r') as f:
                    content = f.read()

                assert 'MY_VAR<<ghadelimiter_' in content
                assert 'my value' in content
        finally:
            os.unlink(temp_path)
            os.environ.pop('MY_VAR', None)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_export_fallback_command(self, mock_stdout):
        '''Test export using command-based fallback'''
        with patch.dict(os.environ, {}, clear=True):
            export_variable(name='TEST_VAR', value=42)

            assert os.environ['TEST_VAR'] == '42'
            output = mock_stdout.getvalue()
            assert '::set-env name=TEST_VAR::42' in output

        os.environ.pop('TEST_VAR', None)


class TestSetSecret:
    '''Test cases for set_secret function'''

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_set_secret_string(self, mock_stdout):
        '''Test masking a string secret'''
        set_secret(secret='my-password-123')
        output = mock_stdout.getvalue()
        assert '::add-mask::my-password-123' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_set_secret_complex(self, mock_stdout):
        '''Test masking complex values'''
        set_secret(secret={'apiKey': 'secret-key'})
        output = mock_stdout.getvalue()
        assert '::add-mask::{"apiKey":"secret-key"}' in output

    @patch('action_toolkit.core.internals.commands.issue_command')
    def test_set_secret_with_error(self, mock_issue_command):
        '''Test warning when add-mask fails'''
        mock_issue_command.side_effect = Exception("Command not supported")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            set_secret(secret='test-secret')

            assert len(w) == 1
            assert "WARNING" in str(w[0].message)
            assert "add-mask command" in str(w[0].message)


class TestAddPath:
    '''Test cases for add_path function'''

    def test_add_path_with_file(self):
        '''Test adding path using file-based approach'''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        original_path = os.environ.get('PATH', '')

        try:
            with patch.dict(os.environ, {WorkflowEnv.GITHUB_PATH: temp_path}):
                add_path(path='/usr/local/bin')

                assert os.environ['PATH'].startswith('/usr/local/bin')

                with open(temp_path, 'r') as f:
                    content = f.read()

                assert '/usr/local/bin' in content
        finally:
            os.unlink(temp_path)
            os.environ['PATH'] = original_path


    def test_add_path_with_path_object(self):
        '''Test adding Path object'''
        original_path = os.environ.get('PATH', '')
        path_to_add = Path.home() / '.local' / 'bin'

        try:
            with patch.dict(os.environ, {'PATH': original_path}):
                add_path(path=path_to_add)
                assert str(path_to_add) in os.environ['PATH']
        finally:
            os.environ['PATH'] = original_path

    def test_add_path_empty_original(self):
        '''Test adding path when PATH is empty'''
        with patch.dict(os.environ, {'PATH': ''}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                add_path(path='/new/path')

                assert len(w) == 1
                assert "PATH environment variable is not set" in str(w[0].message)
                assert os.environ['PATH'] == f"/new/path{os.pathsep}"


class TestState:
    '''Test cases for save_state and get_state functions'''

    def test_save_state_with_file(self):
        '''Test saving state using file-based approach'''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            with patch.dict(os.environ, {WorkflowEnv.GITHUB_STATE: temp_path}):
                save_state(name='build_id', value='12345')

                with open(temp_path, 'r') as f:
                    content = f.read()

                assert 'build_id<<ghadelimiter_' in content
                assert '12345' in content
        finally:
            os.unlink(temp_path)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_save_state_fallback_command(self, mock_stdout):
        '''Test saving state using command-based fallback'''
        with patch.dict(os.environ, {}, clear=True):
            save_state(name='counter', value=42)

            output = mock_stdout.getvalue()
            assert '::save-state name=counter::42' in output

    def test_get_state(self):
        '''Test retrieving saved state'''
        with patch.dict(os.environ, {'STATE_build_id': '12345'}):
            result = get_state(name='build_id')
            assert result == '12345'

    def test_get_state_missing(self):
        '''Test retrieving missing state'''
        with patch.dict(os.environ, {}, clear=True):
            result = get_state(name='missing')
            assert result == ''


class TestLogging:
    '''Test cases for logging functions'''

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_debug(self, mock_stdout):
        '''Test debug logging'''
        debug(message='Debug information')
        output = mock_stdout.getvalue()
        assert '::debug::Debug information' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_notice_simple(self, mock_stdout):
        '''Test simple notice'''
        notice('Important message')
        output = mock_stdout.getvalue()
        assert '::notice::Important message' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_notice_with_properties(self, mock_stdout):
        '''Test notice with annotation properties'''
        props = AnnotationProperties(
            title='Build Notice',
            file='build.py',
            startLine=42
        )
        notice('Build completed', properties=props)

        output = mock_stdout.getvalue()
        assert '::notice' in output
        assert 'title=Build Notice' in output
        assert 'file=build.py' in output
        # NOTE: Current implementation doesn't map startLine to line
        assert 'line=42' in output  # Should be 'line=42' in correct implementation

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_warning_string(self, mock_stdout):
        '''Test warning with string message'''
        warning('Deprecated function')
        output = mock_stdout.getvalue()
        assert '::warning::Deprecated function' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_warning_exception(self, mock_stdout):
        '''Test warning with exception'''
        exc = ValueError('Invalid configuration')
        warning(exc)
        output = mock_stdout.getvalue()
        assert '::warning::Invalid configuration' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_error_with_properties(self, mock_stdout):
        '''Test error with annotation properties'''
        props = AnnotationProperties(
            title='Syntax Error',
            file='main.py',
            startLine=10,
            endLine=10,
            startColumn=5,
            endColumn=15
        )
        error('Undefined variable', properties=props)

        output = mock_stdout.getvalue()
        assert '::error' in output
        assert 'Undefined variable' in output
        assert 'title=Syntax Error' in output


class TestGrouping:
    '''Test cases for grouping functions'''

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_start_end_group(self, mock_stdout):
        '''Test start and end group'''
        start_group(name='Build Steps')
        output = mock_stdout.getvalue()
        assert '::group::Build Steps' in output

        mock_stdout.truncate(0)
        mock_stdout.seek(0)

        end_group()
        output = mock_stdout.getvalue()
        assert '::endgroup::' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_group_context_manager(self, mock_stdout):
        '''Test group context manager'''
        with group(name='Test Section'):
            pass

        output = mock_stdout.getvalue()
        assert '::group::Test Section' in output
        assert '::endgroup::' in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_group_context_manager_with_exception(self, mock_stdout):
        '''Test group context manager handles exceptions'''
        try:
            with group(name='Error Section'):
                raise ValueError('Test error')
        except ValueError:
            pass

        output = mock_stdout.getvalue()
        # should still close the group
        assert '::group::Error Section' in output
        assert '::endgroup::' in output