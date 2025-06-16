'''Tests for action_toolkit.internals.exception module'''

import pytest
from action_toolkit.internals.exception import BaseActionError


class TestBaseActionError:
    '''Test cases for BaseActionError'''

    def test_basic_exception(self):
        '''Test basic exception creation'''
        error = BaseActionError("Something went wrong")
        assert "PyActionToolkit.BaseActionError: Something went wrong." in str(error)
        assert "<cause=N/A>" in str(error)

    def test_exception_with_cause(self):
        '''Test exception with underlying cause'''
        cause = ValueError("Invalid value")
        error = BaseActionError("Operation failed", cause=cause)
        assert "PyActionToolkit.BaseActionError: Operation failed." in str(error)
        assert "<cause=ValueError>" in str(error)

    def test_exception_inheritance(self):
        '''Test that BaseActionError inherits from Exception'''
        error = BaseActionError("Test error")
        assert isinstance(error, Exception)

    def test_exception_message_format(self):
        '''Test the exception message format'''
        error = BaseActionError("Custom message")
        expected = "PyActionToolkit.BaseActionError: Custom message.\n<cause=N/A>"
        assert error.message == expected

    def test_exception_can_be_caught(self):
        '''Test that the exception can be caught properly'''
        with pytest.raises(BaseActionError) as exc_info:
            raise BaseActionError("Test error")

        assert "Test error" in str(exc_info.value)

    def test_subclass_formatting(self):
        '''Test that subclasses format correctly'''
        class CustomError(BaseActionError):
            pass

        error = CustomError("Custom error")
        assert "PyActionToolkit.CustomError: Custom error." in str(error)