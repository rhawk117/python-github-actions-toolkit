'''Tests for core.internals.commands module'''

import io
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from action_toolkit.core.internals.commands import (
    to_command_value,
    to_command_properties,
    escape_data,
    escape_property,
    Command,
    issue_command,
    issue,
    issue_file_command,
    prepare_key_value_message
)
from action_toolkit.core.internals.types import WorkflowCommand, AnnotationProperties


class TestToCommandValue:
    '''Test cases for to_command_value function'''

    def test_none_value(self):
        '''Test None returns empty string'''
        assert to_command_value(input=None) == ''

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ('hello', 'hello'),
            (True, 'true'),
            (False, 'false'),
            ('', ''),
            ('with spaces', 'with spaces'),
            (42, '42'),
            (3.14, '3.14'),
            (0, '0'),
            (-10, '-10'),
            ([1,2,3], '[1,2,3]'),
            ([], '[]'),
            (['a', 'b'], '["a","b"]'),
            ({'key': 'value'}, '{"key":"value"}'),
            ({}, '{}'),
            (['Hello 世界'], '["Hello 世界"]'),
        ]
    )
    def test_json_serializable(self, input_value, expected):
        '''Test list values are JSON serialized'''
        assert to_command_value(input=input_value) == expected, (
            f'Expected {expected} for input {input_value} got {to_command_value(input=input_value)}'
        )

    def test_non_serializable_fallback(self):
        '''Test non-JSON serializable objects fall back to str()'''
        class CustomObject:
            def __str__(self):
                return 'custom_string'

        obj = CustomObject()
        assert to_command_value(input=obj) == 'custom_string'


class TestToCommandProperties:
    '''Test cases for to_command_properties function'''

    def test_empty_properties(self):
        '''Test empty annotation properties'''
        props = AnnotationProperties()
        result = to_command_properties(props)
        assert result == {}

    def test_all_properties(self):
        '''Test all annotation properties with mapping'''
        props = AnnotationProperties(
            title='Error',
            file='main.py',
            startLine=42,
            endLine=45,
            startColumn=10,
            endColumn=20
        )

        # NOTE: This test reveals an issue - the current implementation
        # uses dataclass_utils.dump_dataclass which doesn't handle the
        # property name mappings (startLine -> line, etc.)
        result = to_command_properties(props)

        assert result == {
            'title': 'Error',
            'file': 'main.py',
            'line': 42,
            'endLine': 45,
            'col': 10,
            'endColumn': 20
        }


    def test_partial_properties(self):
        '''Test partial annotation properties'''
        props = AnnotationProperties(
            file='test.py',
            startLine=10
        )
        result = to_command_properties(props)

        assert 'title' not in result
        assert result['file'] == 'test.py'
        assert result['startLine'] == 10


class TestEscapeFunctions:
    '''Test cases for escape functions'''

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ('hello%world', 'hello%25world'),
            ('line1\rline2', 'line1%0Dline2'),
            ('line1\nline2', 'line1%0Aline2'),
            ('test%\r\n', 'test%25%0D%0A'),
            (123, '123'),
            (True, 'true')
        ]
    )
    def test_escape_data(self, input_value, expected):
        '''Test data escaping for command messages'''
        assert escape_data(input_value) == expected, (
            f'Expected {expected} for input {input_value} got {escape_data(input_value)}'
        )

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ('hello:world', 'hello%3Aworld'),
            ('key,value', 'key%2Cvalue'),
            ('test%:\r\n,', 'test%25%3A%0D%0A%2C'),
            ('all%:\r\n,special', 'all%25%3A%0D%0A%2Cspecial'),
            ('%%', '%25%25'),
            ('%', '%25')
        ]
    )
    def test_escape_property(self, input_value, expected):
        '''Test property escaping for command properties'''
        assert escape_property(input_value) == expected, (
            f'Expected {expected} for input {input_value} got {escape_property(input_value)}'
        )


class TestCommand:
    '''Test cases for Command class'''

    def test_basic_command(self):
        '''Test basic command formatting'''
        cmd = Command(
            command=WorkflowCommand.DEBUG,
            properties={},
            message='hello'
        )
        assert cmd.as_string() == '::debug::hello'

    def test_command_with_properties(self):
        '''Test command with properties'''
        cmd = Command(
            command=WorkflowCommand.SET_OUTPUT,
            properties={'name': 'myOutput'},
            message='value123'
        )
        assert cmd.as_string() == '::set-output name=myOutput::value123'

    def test_command_with_multiple_properties(self):
        '''Test command with multiple properties'''
        cmd = Command(
            command=WorkflowCommand.WARNING,
            properties={'file': 'test.py', 'line': '10'},
            message='This is a warning'
        )
        result = cmd.as_string()

        # Properties order might vary
        assert result.startswith('::warning ')
        assert 'file=test.py' in result
        assert 'line=10' in result
        assert result.endswith('::This is a warning')

    def test_command_with_none_properties(self):
        '''Test that None property values are skipped'''
        cmd = Command(
            command=WorkflowCommand.ERROR,
            properties={'key1': 'value1', 'key2': None, 'key3': 'value3'},
            message='msg'
        )
        result = cmd.as_string()

        assert 'key1=value1' in result
        assert 'key2' not in result
        assert 'key3=value3' in result

    def test_command_property_escaping(self):
        '''Test that properties are properly escaped'''
        cmd = Command(
            command=WorkflowCommand.SET_ENV,
            properties={'name': 'KEY:VALUE', 'other': 'a,b'},
            message='test'
        )
        result = cmd.as_string()

        assert 'name=KEY%3AVALUE' in result
        assert 'other=a%2Cb' in result

    def test_command_message_escaping(self):
        '''Test that messages are properly escaped'''
        cmd = Command(
            command=WorkflowCommand.DEBUG,
            properties={},
            message='Line1\nLine2\rLine3%'
        )
        assert cmd.as_string() == '::debug::Line1%0ALine2%0DLine3%25'

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_command_write(self, mock_stdout):
        '''Test writing command to stdout'''
        cmd = Command(
            command=WorkflowCommand.NOTICE,
            properties={},
            message='Test message'
        )
        cmd.write()

        output = mock_stdout.getvalue()
        assert output == '::notice::Test message' + os.linesep

    def test_command_repr(self):
        '''Test command string representation'''
        cmd = Command(
            command=WorkflowCommand.ERROR,
            properties={'file': 'test.py'},
            message='Error!'
        )
        repr_str = repr(cmd)

        assert 'Command(' in repr_str
        assert 'error' in repr_str
        assert 'test.py' in repr_str
        assert 'Error!' in repr_str


class TestIssueCommand:
    '''Test cases for issue_command function'''

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_issue_command_basic(self, mock_stdout):
        '''Test basic command issuing'''
        issue_command(
            command=WorkflowCommand.DEBUG,
            message='Debug message'
        )

        output = mock_stdout.getvalue()
        assert output.strip() == '::debug::Debug message'

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_issue_command_with_properties(self, mock_stdout):
        '''Test command with properties'''
        issue_command(
            command=WorkflowCommand.SET_OUTPUT,
            properties={'name': 'result'},
            message='success'
        )

        output = mock_stdout.getvalue()
        assert output.strip() == '::set-output name=result::success'

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_issue_command_default_message(self, mock_stdout):
        '''Test command with default empty message'''
        issue_command(command=WorkflowCommand.ENDGROUP)

        output = mock_stdout.getvalue()
        assert output.strip() == '::endgroup::'


class TestIssue:
    '''Test cases for issue function'''

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_issue_simple(self, mock_stdout):
        '''Test simple issue function'''
        issue(name=WorkflowCommand.GROUP, message='My Group')

        output = mock_stdout.getvalue()
        assert output.strip() == '::group::My Group'

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_issue_empty_message(self, mock_stdout):
        '''Test issue with empty message'''
        issue(name=WorkflowCommand.ENDGROUP)

        output = mock_stdout.getvalue()
        assert output.strip() == '::endgroup::'


class TestIssueFileCommand:
    '''Test cases for issue_file_command function'''

    def test_file_command_with_path(self):
        '''Test file command with direct file path'''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            issue_file_command(
                'OUTPUT',
                'test message',
                file_path=temp_path
            )

            with open(temp_path, 'r') as f:
                content = f.read()

            assert content == 'test message' + os.linesep
        finally:
            os.unlink(temp_path)

    def test_file_command_with_env_var(self):
        '''Test file command with environment variable'''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            with patch.dict(os.environ, {'TEST_OUTPUT': temp_path}):
                issue_file_command(
                    'OUTPUT',
                    'env var message',
                    env_var='TEST_OUTPUT'
                )

            with open(temp_path, 'r') as f:
                content = f.read()

            assert content == 'env var message' + os.linesep
        finally:
            os.unlink(temp_path)

    def test_file_command_missing_path(self):
        '''Test file command with missing path raises error'''
        with pytest.raises(ValueError, match='Either env_var or file_path must be provided'):
            issue_file_command('OUTPUT', 'message')

    def test_file_command_empty_env_var(self):
        '''Test file command with empty env var raises error'''
        with patch.dict(os.environ, {'EMPTY_VAR': ''}):
            with pytest.raises(ValueError, match='Unable to find file path'):
                issue_file_command(
                    'OUTPUT',
                    'message',
                    env_var='EMPTY_VAR'
                )

    def test_file_command_creates_directory(self):
        '''Test file command creates directory if needed'''
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, 'subdir', 'output.txt')

            issue_file_command(
                'OUTPUT',
                'test message',
                file_path=file_path
            )

            assert os.path.exists(file_path)
            with open(file_path, 'r') as f:
                assert f.read() == 'test message' + os.linesep


class TestPrepareKeyValueMessage:
    '''Test cases for prepare_key_value_message function'''

    def test_simple_key_value(self):
        '''Test simple key-value message preparation'''
        result = prepare_key_value_message('mykey', 'myvalue')

        lines = result.split(os.linesep)
        assert len(lines) == 3
        assert lines[0].startswith('mykey<<ghadelimiter_')
        assert lines[1] == 'myvalue'
        assert lines[2] == lines[0].split('<<')[1]

    def test_complex_value(self):
        '''Test complex value formatting'''
        result = prepare_key_value_message('data', {'key': 'value', 'num': 42})

        lines = result.split(os.linesep)
        assert lines[1] == '{"key":"value","num":42}'

    def test_multiline_value(self):
        '''Test value with newlines'''
        result = prepare_key_value_message('text', 'line1\nline2')

        lines = result.split(os.linesep)
        assert lines[1] == 'line1\nline2'  # Raw newlines preserved in heredoc

    def test_delimiter_uniqueness(self):
        '''Test that delimiter is unique per call'''
        result1 = prepare_key_value_message('key1', 'value1')
        result2 = prepare_key_value_message('key2', 'value2')

        delimiter1 = result1.split('<<')[1].split(os.linesep)[0]
        delimiter2 = result2.split('<<')[1].split(os.linesep)[0]

        assert delimiter1 != delimiter2
        assert delimiter1.startswith('ghadelimiter_')
        assert delimiter2.startswith('ghadelimiter_')