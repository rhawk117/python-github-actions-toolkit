"""Tests for core.inputs module"""

import os

from unittest.mock import patch

import pytest

from action_toolkit.core import inputs
from action_toolkit.core.commands.exceptions import InputError


class TestGetInput:
    """Test cases for get_input function"""

    def test_basic_input(self):
        """Test basic input retrieval"""
        with patch.dict(os.environ, {'INPUT_MY_INPUT': 'test value'}):
            result = inputs.get_input('my-input')
            assert result == 'test value'

    def test_input_with_spaces_in_name(self):
        """Test input with spaces in name"""
        with patch.dict(os.environ, {'INPUT_MY_INPUT_NAME': 'test value'}):
            result = inputs.get_input('my input name')
            assert result == 'test value'

    def test_input_case_insensitive(self):
        """Test that input names are case insensitive"""
        with patch.dict(os.environ, {'INPUT_MYINPUT': 'test value'}):
            result = inputs.get_input('MyInput')
            assert result == 'test value'

    def test_missing_optional_input(self):
        """Test missing optional input returns empty string"""
        with patch.dict(os.environ, {}, clear=True):
            result = inputs.get_input('missing-input')
            assert result == ''

    def test_required_input_present(self):
        """Test required input that exists"""
        with patch.dict(os.environ, {'INPUT_REQUIRED_INPUT': 'value'}):
            result = inputs.get_input('required-input', required=True)
            assert result == 'value'

    def test_required_input_missing(self):
        """Test required input that is missing raises error"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(InputError) as exc_info:
                inputs.get_input('missing-input', required=True)

            assert "Input 'missing-input' is required" in str(exc_info.value)

    def test_required_input_empty(self):
        """Test required input with empty value raises error"""
        with patch.dict(os.environ, {'INPUT_EMPTY': ''}):
            with pytest.raises(InputError) as exc_info:
                inputs.get_input('empty', required=True)

            assert "Input 'empty' is required" in str(exc_info.value)

    def test_trim_whitespace_default(self):
        """Test whitespace trimming by default"""
        with patch.dict(os.environ, {'INPUT_PADDED': '  value  '}):
            result = inputs.get_input('padded')
            assert result == 'value'

    def test_no_trim_whitespace(self):
        """Test disabling whitespace trimming"""
        with patch.dict(os.environ, {'INPUT_PADDED': '  value  '}):
            result = inputs.get_input('padded', trim_whitespace=False)
            assert result == '  value  '

    def test_trim_newlines(self):
        """Test that newlines are trimmed"""
        with patch.dict(os.environ, {'INPUT_MULTILINE': '\nvalue\n'}):
            result = inputs.get_input('multiline')
            assert result == 'value'

    def test_empty_string_not_trimmed_away(self):
        """Test that empty strings after trimming stay empty"""
        with patch.dict(os.environ, {'INPUT_SPACES': '   '}):
            result = inputs.get_input('spaces')
            assert result == ''

    def test_special_characters(self):
        """Test input with special characters"""
        with patch.dict(os.environ, {'INPUT_SPECIAL': 'value!@#$%^&*()'}):
            result = inputs.get_input('special')
            assert result == 'value!@#$%^&*()'


class TestGetMultilineInput:
    """Test cases for get_multiline_input function"""

    def test_basic_multiline(self):
        """Test basic multiline input"""
        with patch.dict(os.environ, {'INPUT_LINES': 'line1\nline2\nline3'}):
            result = inputs.get_multiline_input('lines')
            assert result == ['line1', 'line2', 'line3']

    def test_multiline_with_empty_lines(self):
        """Test multiline with empty lines (default skips them)"""
        with patch.dict(os.environ, {'INPUT_LINES': 'line1\n\nline2\n\n\nline3'}):
            result = inputs.get_multiline_input('lines')
            assert result == ['line1', 'line2', 'line3']

    def test_multiline_keep_empty_lines(self):
        """Test keeping empty lines"""
        with patch.dict(os.environ, {'INPUT_LINES': 'line1\n\nline2\n\n\nline3'}):
            result = inputs.get_multiline_input('lines', skip_empty_lines=False)
            assert result == ['line1', '', 'line2', '', '', 'line3']

    def test_multiline_trim_whitespace(self):
        """Test trimming whitespace from each line"""
        with patch.dict(os.environ, {'INPUT_LINES': '  line1  \n  line2  \n  line3  '}):
            result = inputs.get_multiline_input('lines')
            assert result == ['line1', 'line2', 'line3']

    def test_multiline_no_trim_whitespace(self):
        """Test keeping whitespace on lines"""
        with patch.dict(os.environ, {'INPUT_LINES': '  line1  \n  line2  '}):
            result = inputs.get_multiline_input('lines', trim_whitespace=False)
            assert result == ['  line1  ', '  line2  ']

    def test_multiline_required(self):
        """Test required multiline input"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(InputError):
                inputs.get_multiline_input('missing', required=True)

    def test_empty_multiline_input(self):
        """Test empty multiline input"""
        with patch.dict(os.environ, {'INPUT_EMPTY': ''}):
            result = inputs.get_multiline_input('empty')
            assert result == []

    def test_single_line_input(self):
        """Test single line without newlines"""
        with patch.dict(os.environ, {'INPUT_SINGLE': 'single line'}):
            result = inputs.get_multiline_input('single')
            assert result == ['single line']

    def test_whitespace_only_lines(self):
        """Test lines with only whitespace"""
        with patch.dict(os.environ, {'INPUT_SPACES': 'line1\n   \n\t\nline2'}):
            result = inputs.get_multiline_input('spaces')
            assert result == ['line1', 'line2']

            result = inputs.get_multiline_input('spaces', skip_empty_lines=False, trim_whitespace=True)
            assert result == ['line1', '', '', 'line2']

            result = inputs.get_multiline_input('spaces', skip_empty_lines=False, trim_whitespace=False)
            assert result == ['line1', '   ', '\t', 'line2']

    def test_trailing_newline(self):
        """Test input with trailing newline"""
        with patch.dict(os.environ, {'INPUT_TRAILING': 'line1\nline2\n'}):
            result = inputs.get_multiline_input('trailing')
            assert result == ['line1', 'line2']

            # if you trim whitespace, the trailing newline is removed thus test case will fail
            result = inputs.get_multiline_input('trailing', skip_empty_lines=False, trim_whitespace=False)
            assert result == ['line1', 'line2', '']


class TestGetBoolInput:
    """Test cases for get_bool_input function"""

    @pytest.mark.parametrize(
        'input_value',
        [
            'true',
            'True',
            'TRUE',
            'yes',
            'Yes',
            'YES',
            'on',
            'On',
            'ON',
            'y',
            'Y',
            '1',
        ],
    )
    def test_truthy_values(self, input_value):
        """Test all YAML truthy values"""
        with patch.dict(os.environ, {'INPUT_BOOL': input_value}):
            result = inputs.get_bool_input('bool')
            assert result is True, f'Failed for value: {input_value}'

    @pytest.mark.parametrize(
        'input_value',
        [
            'false',
            'False',
            'FALSE',
            'no',
            'No',
            'NO',
            'off',
            'Off',
            'OFF',
            'n',
            'N',
            '0',
            '',
            'random',
            'maybe',
            'null',
            'undefined',
        ],
    )
    def test_falsy_values(self, input_value):
        """Test YAML falsy values and other strings"""

        with patch.dict(os.environ, {'INPUT_BOOL': input_value}):
            result = inputs.get_bool_input('bool')
            assert result is False, f'Failed for value: {input_value}'

    def test_bool_with_whitespace(self):
        """Test boolean values with whitespace"""
        with patch.dict(os.environ, {'INPUT_BOOL': '  true  '}):
            result = inputs.get_bool_input('bool')
            assert result is True

        with patch.dict(os.environ, {'INPUT_BOOL': '  false  '}):
            result = inputs.get_bool_input('bool', trim_whitespace=False)
            assert result is False  # ' false ' doesn't match any truthy value

    def test_bool_missing_optional(self):
        """Test missing optional boolean input"""
        with patch.dict(os.environ, {}, clear=True):
            result = inputs.get_bool_input('missing')
            assert result is False  # Empty string is falsy

    def test_bool_required(self):
        """Test required boolean input"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(InputError):
                inputs.get_bool_input('missing', required=True)

    def test_bool_case_sensitivity(self):
        """Test case sensitivity is handled correctly"""
        with patch.dict(os.environ, {'INPUT_BOOL': 'YeS'}):
            result = inputs.get_bool_input('bool')
            assert result is True

        with patch.dict(os.environ, {'INPUT_BOOL': 'tRuE'}):
            result = inputs.get_bool_input('bool')
            assert result is True

    def test_bool_numeric_strings(self):
        """Test numeric string values"""
        with patch.dict(os.environ, {'INPUT_BOOL': '1'}):
            result = inputs.get_bool_input('bool')
            assert result is True

        with patch.dict(os.environ, {'INPUT_BOOL': '0'}):
            result = inputs.get_bool_input('bool')
            assert result is False

        with patch.dict(os.environ, {'INPUT_BOOL': '2'}):
            result = inputs.get_bool_input('bool')
            assert result is False

        with patch.dict(os.environ, {'INPUT_BOOL': '-1'}):
            result = inputs.get_bool_input('bool')
            assert result is False
