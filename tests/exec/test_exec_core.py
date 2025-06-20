"""Tests for action_toolkit.exec module"""

import subprocess
import sys

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from action_toolkit.exec import (
    ExecError,
    ExecListeners,
    ExecOptions,
    ExecResult,
    exec,
    exec_async,
    exec_context,
    exec_context_async,
    get_exec_output,
    get_exec_output_async,
)


class TestExecResult:
    """Test cases for ExecResult class"""

    def test_success_property(self):
        """Test success property calculation"""
        success_result = ExecResult(exit_code=0, stdout='output', stderr='', command='test')
        assert success_result.success is True

        failure_result = ExecResult(exit_code=1, stdout='', stderr='error', command='test')
        assert failure_result.success is False


class TestExecOptions:
    """Test cases for ExecOptions class"""

    def test_default_options(self):
        """Test default option values"""
        options = ExecOptions()

        assert options.cwd is None
        assert options.env is None
        assert options.input is None
        assert options.timeout is None
        assert options.silent is False
        assert options.ignore_return_code is False
        assert options.fail_on_stderr is False

    def test_custom_options(self):
        """Test custom option values"""

        options = ExecOptions(
            cwd='/tmp',
            env={'KEY': 'value'},
            input='test input',
            timeout=30.0,
            silent=True,
            ignore_return_code=True,
            fail_on_stderr=True,
        )

        assert options.cwd == Path('/tmp')
        assert options.env == {'KEY': 'value'}
        assert options.input == 'test input'
        assert options.timeout == 30.0
        assert options.silent is True
        assert options.ignore_return_code is True
        assert options.fail_on_stderr is True


class TestExecListeners:
    """Test cases for ExecListeners class"""

    def test_default_listeners(self):
        """Test default listener values"""
        listeners = ExecListeners()

        assert listeners.stdout is None
        assert listeners.stderr is None
        assert listeners.debug is None

    def test_custom_listeners(self):
        """Test custom listener functions"""
        stdout_mock = Mock()
        stderr_mock = Mock()
        debug_mock = Mock()

        listeners = ExecListeners(stdout=stdout_mock, stderr=stderr_mock, debug=debug_mock)

        assert listeners.stdout is stdout_mock
        assert listeners.stderr is stderr_mock
        assert listeners.debug is debug_mock


class TestExec:
    """Test cases for exec function"""

    @patch('subprocess.run')
    def test_successful_execution(self, mock_run):
        """Test successful command execution"""
        mock_run.return_value = Mock(returncode=0, stdout='output line', stderr='')

        result = exec('echo', ['hello'])

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == 'output line'
        assert result.stderr == ''
        assert result.command == 'echo hello'

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_failed_execution(self, mock_run):
        """Test failed command execution"""
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='error message')

        with pytest.raises(ExecError) as exc_info:
            exec('false')

        error = exc_info.value
        assert error.exit_code == 1
        assert error.command == 'false'
        assert 'failed' in str(error)

    @patch('subprocess.run')
    def test_ignore_return_code(self, mock_run):
        """Test ignoring non-zero return codes"""
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='error')

        options = ExecOptions(ignore_return_code=True)
        result = exec('false', options=options)

        assert result.success is False
        assert result.exit_code == 1

    @patch('subprocess.run')
    def test_fail_on_stderr(self, mock_run):
        """Test failing when stderr has content"""
        mock_run.return_value = Mock(returncode=0, stdout='output', stderr='warning message')

        options = ExecOptions(fail_on_stderr=True)

        with pytest.raises(ExecError) as exc_info:
            exec('command', options=options)

        assert 'produced stderr output' in str(exc_info.value)

    @patch('subprocess.run')
    def test_with_input(self, mock_run):
        """Test command with input"""
        mock_run.return_value = Mock(returncode=0, stdout='processed', stderr='')

        options = ExecOptions(input='test input')
        exec('cat', options=options)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[1]['input'] == 'test input'

    @patch('subprocess.run')
    def test_with_cwd(self, mock_run):
        """Test command with working directory"""
        mock_run.return_value = Mock(returncode=0, stdout='/tmp', stderr='')

        options = ExecOptions(cwd='/tmp')
        exec('pwd', options=options)

        call_args = mock_run.call_args
        assert call_args[1]['cwd'] == Path('/tmp')

    @patch('subprocess.run')
    def test_with_env(self, mock_run):
        """Test command with environment variables"""
        mock_run.return_value = Mock(returncode=0, stdout='value', stderr='')

        options = ExecOptions(env={'CUSTOM_VAR': 'value'})
        exec('echo', ['$CUSTOM_VAR'], options=options)

        call_args = mock_run.call_args
        env = call_args[1]['env']
        assert 'CUSTOM_VAR' in env
        assert env['CUSTOM_VAR'] == 'value'

    @patch('subprocess.run')
    def test_timeout_error(self, mock_run):
        """Test command timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired(['sleep', '10'], 1)

        options = ExecOptions(timeout=1.0)

        with pytest.raises(ExecError) as exc_info:
            exec('sleep', ['10'], options=options)

        assert 'timed out' in str(exc_info.value)

    @patch('subprocess.run')
    def test_file_not_found(self, mock_run):
        """Test command not found"""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(ExecError) as exc_info:
            exec('nonexistent-command')

        assert 'not found' in str(exc_info.value)

    @patch('subprocess.run')
    def test_listeners(self, mock_run):
        """Test output listeners"""
        mock_run.return_value = Mock(returncode=0, stdout='line1\nline2', stderr='error1\nerror2')

        stdout_lines = []
        stderr_lines = []

        listeners = ExecListeners(
            stdout=lambda line: stdout_lines.append(line), stderr=lambda line: stderr_lines.append(line)
        )

        exec('command', listeners=listeners)

        assert stdout_lines == ['line1', 'line2']
        assert stderr_lines == ['error1', 'error2']


class TestExecAsync:
    """Test cases for exec_async function"""

    @pytest.mark.asyncio
    async def test_successful_async_execution(self):
        """Test successful async command execution"""
        # Use a simple command that should work on most systems
        result = await exec_async('python', ['--version'])

        assert result.success is True
        assert result.exit_code == 0
        assert 'Python' in result.stdout or 'Python' in result.stderr

    @pytest.mark.asyncio
    async def test_failed_async_execution(self):
        """Test failed async command execution"""
        with pytest.raises(ExecError):
            await exec_async('python', ['-c', 'exit(1)'])

    @pytest.mark.asyncio
    async def test_async_timeout(self):
        """Test async command timeout"""
        options = ExecOptions(timeout=0.1)

        with pytest.raises(ExecError) as exc_info:
            await exec_async('python', ['-c', 'import time; time.sleep(1)'], options=options)

        assert 'timed out' in str(exc_info.value)


class TestExecContext:
    """Test cases for exec_context function"""

    @patch('subprocess.run')
    def test_exec_context(self, mock_run):
        """Test execution context manager"""
        mock_run.return_value = Mock(returncode=0, stdout='test', stderr='')

        with exec_context(cwd='/tmp', env={'TEST': 'value'}) as ctx:
            assert ctx.cwd == Path('/tmp')
            assert ctx.env == {'TEST': 'value'}

            exec('command', options=ctx)

        call_args = mock_run.call_args
        assert call_args[1]['cwd'] == Path('/tmp')

    @pytest.mark.asyncio
    async def test_exec_context_async(self):
        """Test async execution context manager"""
        async with exec_context_async(cwd=Path.cwd()) as ctx:
            assert ctx.cwd == Path.cwd()

            result = await exec_async('python', ['--version'], options=ctx)
            assert result.success is True


class TestGetExecOutput:
    """Test cases for get_exec_output function"""

    @patch('subprocess.run')
    def test_get_output(self, mock_run):
        """Test getting command output"""
        mock_run.return_value = Mock(returncode=0, stdout='expected output', stderr='')

        output = get_exec_output('echo', ['hello'])
        assert output == 'expected output'

    @pytest.mark.asyncio
    async def test_get_output_async(self):
        """Test getting async command output"""
        output = await get_exec_output_async('python', ['--version'])
        assert 'Python' in output or len(output) > 0


class TestExecError:
    """Test cases for ExecError exception"""

    def test_exec_error_creation(self):
        """Test ExecError exception creation"""
        error = ExecError(
            command='test command', exit_code=1, stdout='output', stderr='error', message='Custom message'
        )

        assert error.command == 'test command'
        assert error.exit_code == 1
        assert error.stdout == 'output'
        assert error.stderr == 'error'
        assert 'Custom message' in str(error)

    def test_exec_error_default_message(self):
        """Test ExecError with default message"""
        error = ExecError(command='failed-command', exit_code=2)

        assert 'failed with exit code 2' in str(error)


@pytest.mark.integration
class TestExecIntegration:
    """Integration tests using real commands"""

    def test_python_version(self):
        """Test getting Python version"""
        result = exec('python', ['--version'])

        assert result.success is True
        version_output = result.stdout + result.stderr
        assert 'Python' in version_output

    def test_echo_command(self):
        """Test simple echo command"""
        if sys.platform.startswith('win'):
            result = exec('cmd', ['/c', 'echo', 'hello world'])
        else:
            result = exec('echo', ['hello world'])

        assert result.success is True
        assert 'hello world' in result.stdout

    def test_working_directory(self):
        """Test command with working directory"""
        options = ExecOptions(cwd=Path.cwd().parent)

        if sys.platform.startswith('win'):
            result = exec('cmd', ['/c', 'cd'], options=options)
        else:
            result = exec('pwd', options=options)

        assert result.success is True
        assert str(Path.cwd().parent) in result.stdout

    @pytest.mark.asyncio
    async def test_async_python_version(self):
        """Test async Python version"""
        result = await exec_async('python', ['--version'])

        assert result.success is True
        version_output = result.stdout + result.stderr
        assert 'Python' in version_output
