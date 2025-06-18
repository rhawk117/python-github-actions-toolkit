'''Tests for core.internals.utils module'''

import pytest
from action_toolkit.core.internals.utils import (
    parse_yaml_boolean,
    get_input_name,
    split_lines,
    is_valid_url
)


class TestParseYamlBoolean:
    '''Test cases for parse_yaml_boolean function'''

    @pytest.mark.parametrize(
        "value",
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
        ]
    )
    def test_truthy_values(self, value) -> None:
        '''Test all YAML truthy values'''
        assert parse_yaml_boolean(value) is True, f"Failed for value: {value}"

    @pytest.mark.parametrize(
        "value",
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
        ]
    )
    def test_falsy_values(self, value):
        '''Test YAML falsy values and other strings'''
        assert parse_yaml_boolean(value) is False, f"Failed for value: {value}"

    @pytest.mark.parametrize(
        "value",
        [
            '',
            'random',
            'True123',
            '123',
            'yesno',
            'maybe',
            'null',
            'None',
            'undefined',
        ]
    )
    def test_arbitrary_strings(self, value):
        '''Test arbitrary strings return False'''
        assert parse_yaml_boolean(value) is False, f"Failed for value: {value}"

    def test_whitespace_handling(self):
        '''Test values with whitespace'''
        # These should be false because they don't match exactly
        assert parse_yaml_boolean(' true') is False
        assert parse_yaml_boolean('true ') is False
        assert parse_yaml_boolean(' yes ') is False


class TestGetInputName:
    '''Test cases for get_input_name function'''

    def test_simple_name(self):
        '''Test simple input name conversion'''
        assert get_input_name('myinput') == 'INPUT_MYINPUT'
        assert get_input_name('test') == 'INPUT_TEST'

    def test_hyphenated_name(self):
        '''Test hyphenated input names'''
        assert get_input_name('my-input') == 'INPUT_MY_INPUT'
        assert get_input_name('api-key-value') == 'INPUT_API_KEY_VALUE'

    def test_space_separated_name(self):
        '''Test space-separated input names'''
        assert get_input_name('my input') == 'INPUT_MY_INPUT'
        assert get_input_name('test input name') == 'INPUT_TEST_INPUT_NAME'

    def test_mixed_separators(self):
        '''Test names with mixed separators'''
        assert get_input_name('my-input name') == 'INPUT_MY_INPUT_NAME'
        assert get_input_name('test input-name') == 'INPUT_TEST_INPUT_NAME'

    def test_already_uppercase(self):
        '''Test names that are already uppercase'''
        assert get_input_name('MYINPUT') == 'INPUT_MYINPUT'
        assert get_input_name('MY-INPUT') == 'INPUT_MY_INPUT'

    def test_empty_string(self):
        '''Test empty string input'''
        assert get_input_name('') == 'INPUT_'

    def test_special_characters(self):
        '''Test that only spaces and hyphens are replaced'''
        # Other special characters are kept
        assert get_input_name('my_input') == 'INPUT_MY_INPUT'
        assert get_input_name('my.input') == 'INPUT_MY.INPUT'
        assert get_input_name('my@input') == 'INPUT_MY@INPUT'


class TestSplitLines:
    '''Test cases for split_lines function'''

    def test_basic_split(self):
        '''Test basic line splitting'''
        input_str = 'line1\nline2\nline3'
        result = split_lines(input_str)
        assert result == ['line1', 'line2', 'line3']

    def test_skip_empty_lines(self):
        '''Test skipping empty lines (default behavior)'''
        input_str = 'line1\n\nline2\n\n\nline3'
        result = split_lines(input_str)
        assert result == ['line1', 'line2', 'line3']

    def test_keep_empty_lines(self):
        '''Test keeping empty lines'''
        input_str = 'line1\n\nline2\n\n\nline3'
        result = split_lines(input_str, skip_empty=False)
        assert result == ['line1', '', 'line2', '', '', 'line3']

    def test_whitespace_only_lines(self):
        '''Test handling of whitespace-only lines'''
        input_str = 'line1\n   \nline2\n\t\nline3'
        result = split_lines(input_str)
        assert result == ['line1', 'line2', 'line3']

        result = split_lines(input_str, skip_empty=False)
        assert result == ['line1', '   ', 'line2', '\t', 'line3']

    def test_empty_string(self):
        '''Test empty string input'''
        assert split_lines('') == []
        assert split_lines('', skip_empty=False) == ['']

    def test_single_line(self):
        '''Test single line without newlines'''
        assert split_lines('single line') == ['single line']

    def test_trailing_newline(self):
        '''Test string with trailing newline'''
        input_str = 'line1\nline2\n'
        assert split_lines(input_str) == ['line1', 'line2']
        assert split_lines(input_str, skip_empty=False) == ['line1', 'line2', '']


class TestIsValidUrl:
    '''Test cases for is_valid_url function'''

    @pytest.mark.parametrize(
        "url",
        [
            'http://example.com',
            'https://example.com',
            'https://example.com/path',
            'http://example.com:8080',
            'https://example.com/path?query=value',
            'ftp://files.example.com',
            'https://sub.domain.example.com',
            'http://192.168.1.1',
            'https://example.com/path#anchor',
            'https://example.com/path%20with%20spaces',
        ]
    )
    def test_valid_urls(self, url):
        '''Test valid URLs'''
        assert is_valid_url(url) is True, f"Failed for URL: {url}"

    @pytest.mark.parametrize(
        "url",
        [
            '',
            'not a url',
            'example.com',  # Missing scheme
            'http://',  # Missing netloc
            'http:example.com',  # Invalid format
            '//example.com',  # Missing scheme
            'javascript:alert(1)',  # Has scheme but no netloc
            'file:///path/to/file',  # Has scheme but no netloc
            'mailto:user@example.com',  # Has scheme but no netloc

        ]
    )
    def test_invalid_urls(self, url):
        '''Test invalid URLs'''
        assert is_valid_url(url) is False, f"Failed for URL: {url}"

    def test_edge_cases(self):
        '''Test edge cases'''
        try:
            result = is_valid_url(None)  # type: ignore
            assert result is False
        except:
            pass  # Expected

        assert is_valid_url('https://example.com/path%20with%20spaces') is True
        assert is_valid_url('https://example.com/日本語') is True