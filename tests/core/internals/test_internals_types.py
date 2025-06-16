'''Tests for core.internals.types module'''

import pytest
from action_toolkit.core.internals.types import (
    WorkflowCommand,
    AnnotationProperties,
    WorkflowEnv,
    YAML_BOOLEAN_TRUE,
    YAML_BOOLEAN_FALSE
)
from action_toolkit.core.internals.exceptions import AnnotationError




class TestWorkflowCommand:
    '''Test cases for WorkflowCommand enum'''
    @pytest.mark.parametrize(
        "command,value",
        [
            (WorkflowCommand.SET_OUTPUT, 'set-output'),
            (WorkflowCommand.SET_ENV, 'set-env'),
            (WorkflowCommand.ADD_PATH, 'add-path'),
            (WorkflowCommand.DEBUG, 'debug'),
            (WorkflowCommand.NOTICE, 'notice'),
            (WorkflowCommand.WARNING, 'warning'),
            (WorkflowCommand.ERROR, 'error'),
            (WorkflowCommand.GROUP, 'group'),
            (WorkflowCommand.ENDGROUP, 'endgroup'),
            (WorkflowCommand.SAVE_STATE, 'save-state'),
            (WorkflowCommand.ADD_MASK, 'add-mask'),
            (WorkflowCommand.ECHO, 'echo'),
            (WorkflowCommand.FILE_COMMAND, 'file-command')
        ]
    )
    def test_command_values(self, command, value):
        '''Test workflow command string values'''
        assert command == value, f"Expected {command} to be '{value}'"

    def test_command_string_conversion(self):
        '''Test that commands can be used as strings'''
        assert str(WorkflowCommand.DEBUG) == 'debug'
        assert f"{WorkflowCommand.ERROR}" == 'error'

    def test_command_value_access(self):
        '''Test accessing the string value'''
        assert WorkflowCommand.WARNING.value == 'warning'



class TestAnnotationProperties:
    '''Test cases for AnnotationProperties dataclass'''

    def test_create_empty(self):
        '''Test creating empty annotation properties'''
        props = AnnotationProperties()
        assert props.title is None
        assert props.file is None
        assert props.startLine is None
        assert props.endLine is None
        assert props.startColumn is None
        assert props.endColumn is None


    def test_frozen_dataclass(self):
        '''Test that AnnotationProperties is frozen'''
        props = AnnotationProperties(title="Test")

        with pytest.raises(AttributeError):
            props.title = "Modified"  # type: ignore

    def test_valid_column_with_same_lines(self):
        '''Test that columns are valid when lines are the same'''
        props = AnnotationProperties(
            startLine=10,
            endLine=10,
            startColumn=5,
            endColumn=15
        )
        assert props.startColumn == 5
        assert props.endColumn == 15

    def test_invalid_column_with_different_lines(self):
        '''Test that columns are invalid when lines differ'''
        with pytest.raises(AnnotationError) as exc_info:
            AnnotationProperties(
                startLine=10,
                endLine=20,
                startColumn=5,
                endColumn=15
            )

        assert "startColumn and endColumn cannot be sent" in str(exc_info.value)

    def test_column_without_line_difference(self):
        '''Test columns when endLine is None'''
        props = AnnotationProperties(
            startLine=10,
            endLine=None,
            startColumn=5,
            endColumn=15
        )
        assert props.startColumn == 5


class TestWorkflowEnv:
    '''Test cases for WorkflowEnv enum'''

    @pytest.mark.parametrize(
        "env_var,expected_value",
        [
            (WorkflowEnv.GITHUB_OUTPUT, 'GITHUB_OUTPUT'),
            (WorkflowEnv.GITHUB_STATE, 'GITHUB_STATE'),
            (WorkflowEnv.GITHUB_PATH, 'GITHUB_PATH'),
            (WorkflowEnv.GITHUB_ENV, 'GITHUB_ENV'),
            (WorkflowEnv.RUNNER_DEBUG, 'RUNNER_DEBUG'),
            (WorkflowEnv.GITHUB_WORKSPACE, 'GITHUB_WORKSPACE'),
            (WorkflowEnv.GITHUB_ACTION, 'GITHUB_ACTION'),
            (WorkflowEnv.GITHUB_ACTION_PATH, 'GITHUB_ACTION_PATH')
        ]
    )
    def test_env_var_names(self, env_var, expected_value):
        '''Test environment variable name values'''
        assert env_var.value == expected_value, (
            f"Expected {env_var} to be '{expected_value}'"
        )

    def test_env_var_usage(self):
        '''Test that env vars can be used with os.environ'''
        assert isinstance(WorkflowEnv.GITHUB_OUTPUT.value, str)

        env_var = WorkflowEnv.GITHUB_OUTPUT
        assert env_var.value == 'GITHUB_OUTPUT'


class TestYamlBooleanConstants:
    '''Test cases for YAML boolean constants'''

    def test_yaml_true_values(self):
        '''Test YAML truthy values set'''
        expected = {'true', 'yes', 'on', 'y', '1'}
        assert YAML_BOOLEAN_TRUE == expected

        assert 'true' in YAML_BOOLEAN_TRUE
        assert 'TRUE' not in YAML_BOOLEAN_TRUE

    def test_yaml_false_values(self):
        '''Test YAML falsy values set'''
        expected = {'false', 'no', 'off', 'n', '0'}
        assert YAML_BOOLEAN_FALSE == expected
        assert 'false' in YAML_BOOLEAN_FALSE
        assert 'FALSE' not in YAML_BOOLEAN_FALSE

    def test_yaml_sets_are_frozen(self):
        '''Test that YAML boolean sets are immutable'''
        with pytest.raises(AttributeError):
            YAML_BOOLEAN_TRUE.add('maybe')  # type: ignore

        with pytest.raises(AttributeError):
            YAML_BOOLEAN_FALSE.add('perhaps')  # type: ignore

    def test_yaml_sets_are_disjoint(self):
        '''Test that true and false sets don't overlap'''
        assert YAML_BOOLEAN_TRUE.isdisjoint(YAML_BOOLEAN_FALSE)
