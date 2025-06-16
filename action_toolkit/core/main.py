'''
Core functions for GitHub Actions.

This module provides high-level functions for interacting with GitHub Actions,
mirroring the functionality in @actions/core. It includes functions for:
- Environment variables and paths
- Action inputs and outputs
- Logging and annotations
- Workflow commands and control
- State management
'''

from __future__ import annotations
import os
import sys
from contextlib import contextmanager
import warnings

from . import workflow_cmd
from .utils import (
    parse_yaml_boolean,
    get_input_name,
    split_lines,
)
from .types import (
    ExitCode,
    AnnotationProperties,
    InputOptions,
    MultilineInputOptions,
    StringOrPath,
    WorkflowCommand,
    WorkflowEnv,
    IOValue
)
from .exceptions import InputError





class WorkflowInputs:

    @staticmethod
    def get(name: str, *, options: InputOptions | None = None) -> str:
        '''
        Get the value of an action input.

        This function mirrors getInput in core.ts. It reads input values
        from environment variables set by GitHub Actions.

        Parameters
        ----------
        name : str
            Name of the input to get.
        options : Optional[InputOptions]
            Options for retrieving the input:
            - required: Whether the input is required (raises if missing)
            - trimWhitespace: Whether to trim whitespace (default: True)

        Returns
        -------
        str
            The input value.

        Raises
        ------
        InputError
            If the input is required but not supplied.

        Examples
        --------
        >>> # Get optional input
        >>> value = get_input(name='my-input')

        >>> # Get required input
        >>> value = get_input(
        ...     name='api-key',
        ...     options=InputOptions(required=True)
        ... )

        >>> # Get input without trimming whitespace
        >>> value = get_input(
        ...     name='formatted-text',
        ...     options=InputOptions(trimWhitespace=False)
        ... )
        '''
        if options is None:
            options = InputOptions()

        env_name = get_input_name(name)
        val = os.environ.get(env_name, '')

        if options.required and not val:
            raise InputError(
                input_name=name,
                input_value=val,
                reason=f"Input '{name}' is required but not provided."
            )

        if options.trimWhitespace:
            val = val.strip()

        return val

    @staticmethod
    def get_multiline(
        name: str,
        *,
        options: MultilineInputOptions | None = None
    ) -> list[str]:
        '''
        Get the values of a multiline input.

        This function mirrors getMultilineInput in core.ts. Each line
        of the input value is returned as a separate list element.

        Parameters
        ----------
        name : str
            Name of the input to get.
        options : Optional[MultilineInputOptions]
            Options for retrieving the input, including:
            - All options from InputOptions
            - skipEmptyLines: Whether to filter empty lines (default: True)

        Returns
        -------
        list[str]
            List of input values (one per line).

        Examples
        --------
        >>> # Input value: "line1\\nline2\\n\\nline3"
        >>> lines = get_multiline_input(name='files')
        >>> # Returns: ['line1', 'line2', 'line3']

        >>> # Include empty lines
        >>> lines = get_multiline_input(
        ...     name='files',
        ...     options=MultilineInputOptions(skipEmptyLines=False)
        ... )
        >>> # Returns: ['line1', 'line2', '', 'line3']
        '''
        if options is None:
            options = MultilineInputOptions()

        input_options = InputOptions(
            required=options.required,
            trimWhitespace=options.trimWhitespace
        )
        value = WorkflowInputs.get(name=name, options=input_options)

        lines = split_lines(value, skip_empty=options.skipEmptyLines)

        if options.trimWhitespace:
            lines = [line.strip() for line in lines]

        return lines

    @staticmethod
    def get_bool(
        name: str,
        *,
        options: InputOptions | None = None
    ) -> bool:
        '''
        Get the value of an input as a boolean.

        This function mirrors getBooleanInput in core.ts. Boolean values
        are parsed according to YAML 1.2 specification.

        Parameters
        ----------
        name : str
            Name of the input to get.
        options : Optional[InputOptions]
            Options for retrieving the input.

        Returns
        -------
        bool
            Boolean value of the input.
            True for: 'true', 'True', 'TRUE', 'yes', 'Yes', 'YES',
                    'y', 'Y', 'on', 'On', 'ON', '1'
            False for all other values.

        Examples
        --------
        >>> # Input value: "true"
        >>> enabled = get_boolean_input(name='enable-feature')
        >>> # Returns: True

        >>> # Input value: "yes"
        >>> confirmed = get_boolean_input(name='confirm')
        >>> # Returns: True

        >>> # Input value: "0"
        >>> debug = get_boolean_input(name='debug')
        >>> # Returns: False
        '''
        val = WorkflowInputs.get(name=name, options=options)
        return parse_yaml_boolean(val)


class Action:

    @staticmethod
    def set_output(*, name: str, value: IOValue) -> None:
        '''
        Set the value of an output.

        This function mirrors setOutput in core.ts. Output values can
        be used by subsequent steps in the workflow.

        Parameters
        ----------
        name : str
            Name of the output to set.
        value : IOValue
            Value to store. Non-string values will be JSON stringified.

        Notes
        -----
        The function uses the newer file-based approach (GITHUB_OUTPUT)
        when available, falling back to set-output command for compatibility.

        Examples
        --------
        >>> set_output(name='result', value='success')
        >>> set_output(name='count', value=42)
        >>> set_output(name='data', value={'key': 'value'})
        '''
        output_file = os.environ.get(WorkflowEnv.GITHUB_OUTPUT, None)
        if output_file:
            workflow_cmd.issue_file_command(
                'OUTPUT',
                workflow_cmd.prepare_key_value_message(name, value),
                file_path=output_file
            )
        else:
            workflow_cmd.issue_command(
                command=WorkflowCommand.SET_OUTPUT,
                properties={'name': name},
                message=value # type: ignore[call-arg]
            )


    @staticmethod
    def set_command_echo(*, enabled: bool) -> None:
        '''
        Enable or disable echoing of workflow commands.

        This function mirrors setCommandEcho in core.ts. When enabled,
        workflow commands are echoed to the log.

        Parameters
        ----------
        enabled : bool
            Whether to echo commands.

        Examples
        --------
        >>> # Enable command echoing for debugging
        >>> set_command_echo(enabled=True)

        >>> # Disable command echoing (default)
        >>> set_command_echo(enabled=False)
        '''
        workflow_cmd.issue(
            name=WorkflowCommand.ECHO,
            message='on' if enabled else 'off'
        )


    @staticmethod
    def set_failed(*, message: str | Exception) -> None:
        '''
        Set the action status to failed and exit.

        This function mirrors setFailed in core.ts. It logs an error
        message and exits with a failure code.

        Parameters
        ----------
        message : Union[str, Exception]
            Error message or exception.

        Notes
        -----
        This function does not return - it exits the process with code 1.

        Examples
        --------
        >>> try:
        ...     # Some operation
        ...     result = risky_operation()
        ... except Exception as e:
        ...     set_failed(message=e)
        '''
        ActionLogger.error(message=str(message))
        sys.exit(ExitCode.Failure)

    @staticmethod
    def is_debug() -> bool:
        '''
        Check if runner is in debug mode.

        This function mirrors isDebug in core.ts. Debug mode can be
        enabled by setting the RUNNER_DEBUG secret to '1'.

        Returns
        -------
        bool
            True if runner is in debug mode, False otherwise.

        Examples
        --------
        >>> if is_debug():
        ...     debug(message='Detailed debug information...')
        '''
        return os.environ.get(WorkflowEnv.RUNNER_DEBUG, '0') == '1'

    @staticmethod
    def export_variable(*, name: str, value: IOValue) -> None:
        '''
        Sets an environment variable for this action and future actions in the job.

        Similar exportVariable in core.ts. It sets the variable
        in the current process and also exports it for subsequent actions.

        Parameters
        ----------
        name : str
            The name of the variable to set.
        value : IOValue
            The value of the variable. Will be converted to string.

        Notes
        -----
        The function uses the newer file-based approach (GITHUB_ENV) when
        available, falling back to the set-env command for compatibility.

        Examples
        --------
        >>> export_variable(name='MY_VAR', value='my value')
        >>> export_variable(name='BUILD_NUMBER', value=42)
        '''
        str_value = str(value)

        os.environ[name] = str_value

        env_file = os.environ.get(WorkflowEnv.GITHUB_ENV, None)
        if env_file:
            workflow_cmd.issue_file_command(
                'ENV',
                workflow_cmd.prepare_key_value_message(name, value),
                file_path=env_file
            )
        else:
            workflow_cmd.issue_command(
                command=WorkflowCommand.SET_ENV,
                properties={'name': name},
                message=value
            )

    @staticmethod
    def set_secret(*, secret: str | IOValue) -> None:
        '''
        Register a secret which will get masked from logs.

        This function mirrors setSecret in core.ts. Any future occurrence
        of the secret value in logs will be replaced with ***.

        Parameters
        ----------
        secret : Union[str, IOValue]
            Value to be masked in logs. Will be converted to string.

        Examples
        --------
        >>> set_secret(secret='my-password-123')
        >>> set_secret(secret={'apiKey': 'secret-key'})  # JSON serialized
        '''
        workflow_cmd.issue_command(
            command=WorkflowCommand.ADD_MASK,
            properties={},
            message=secret
        )

    @staticmethod
    def add_path(*, path: StringOrPath) -> None:
        '''
        Prepend a directory to the system PATH.

        This function mirrors addPath in core.ts. The path is added
        to the current process and exported for subsequent actions.

        Parameters
        ----------
        path : Union[str, Path]
            Directory to add to PATH.

        Examples
        --------
        >>> add_path(path='/usr/local/bin')
        >>> add_path(path=Path.home() / '.local' / 'bin')
        '''
        path_str = str(path)

        current_path = os.environ.get('PATH', '')
        if not current_path:
            warnings.warn(
                "The PATH environment variable is not set. "
                "This may cause issues with finding executables.",
                category=RuntimeWarning,
                stacklevel=2
            )

        os.environ['PATH'] = f"{path_str}{os.pathsep}{current_path}"

        path_file = os.environ.get(WorkflowEnv.GITHUB_PATH, None)
        if path_file:
            with open(path_file, 'a', encoding='utf-8') as f:
                f.write(path_str + os.linesep)
        else:
            workflow_cmd.issue_command(
                command=WorkflowCommand.ADD_PATH,
                properties={},
                message=path_str
            )

    @staticmethod
    def save_state(*, name: str, value: IOValue) -> None:
        '''
        Save state for sharing between pre/main/post actions.

        This function mirrors saveState in core.ts. State can be
        retrieved in subsequent action phases using get_state.

        Parameters
        ----------
        name : str
            Name of the state to store.
        value : IOValue
            Value to store. Non-string values will be JSON stringified.

        Notes
        -----
        State is only available within the same action execution.
        It cannot be accessed by other actions or steps.

        Examples
        --------
        >>> # In main action
        >>> save_state(name='temp_dir', value='/tmp/build-123')

        >>> # In post action
        >>> temp_dir = get_state(name='temp_dir')
        '''
        state_file = os.environ.get(WorkflowEnv.GITHUB_STATE, None)
        if state_file:
            workflow_cmd.issue_file_command(
                'STATE',
                workflow_cmd.prepare_key_value_message(name, value),
                file_path=state_file
            )
        else:
            workflow_cmd.issue_command(
                command=WorkflowCommand.SAVE_STATE,
                properties={'name': name},
                message=value
            )

    @staticmethod
    def get_state(*, name: str) -> str:
        '''
        Get the value of a saved state.

        This function mirrors getState in core.ts. Retrieves state
        that was previously saved with save_state.

        Parameters
        ----------
        name : str
            Name of the state to retrieve.

        Returns
        -------
        str
            The state value, or empty string if not found.

        Examples
        --------
        >>> # Retrieve previously saved state
        >>> temp_dir = get_state(name='temp_dir')
        >>> if temp_dir:
        ...     cleanup_temp_dir(temp_dir)
        '''
        return os.environ.get(f'STATE_{name}', '')

class ActionLogger:
    @staticmethod
    def debug(*, message: str) -> None:
        '''
        Write debug message to log.

        This function mirrors debug in core.ts. Debug messages are
        hidden by default unless debug mode is enabled.

        Parameters
        ----------
        message : str
            Debug message.

        Examples
        --------
        >>> debug(message='Entering function X with params Y')
        '''
        workflow_cmd.issue_command(
            command=WorkflowCommand.DEBUG,
            properties={},
            message=message
        )

    @staticmethod
    def notice(
        *,
        message: str,
        properties: AnnotationProperties | None = None
    ) -> None:
        '''
        Write a notice message to log.

        This function mirrors notice in core.ts. Notices create
        annotations that are shown prominently in the UI.

        Parameters
        ----------
        message : str
            Notice message.
        properties : Optional[AnnotationProperties]
            Properties to control annotation appearance and location.

        Examples
        --------
        >>> notice(message='Deployment completed successfully')

        >>> notice(
        ...     message='Configuration updated',
        ...     properties=AnnotationProperties(
        ...         title='Config Change',
        ...         file='config.yaml',
        ...         startLine=10
        ...     )
        ... )
        '''
        cmd_properties = workflow_cmd.to_command_properties(
            annotation_properties=properties or AnnotationProperties()
        )
        workflow_cmd.issue_command(
            command=WorkflowCommand.NOTICE,
            properties=cmd_properties,
            message=message
        )

    @staticmethod
    def warning(
        *,
        message: str | Exception,
        properties: AnnotationProperties | None = None
    ) -> None:
        '''
        Write a warning message to log.

        This function mirrors warning in core.ts. Warnings create
        yellow annotations in the workflow summary.

        Parameters
        ----------
        message : Union[str, Exception]
            Warning message or exception.
        properties : Optional[AnnotationProperties]
            Properties to control annotation appearance and location.

        Examples
        --------
        >>> warning(message='Deprecated function used')

        >>> warning(
        ...     message='Low disk space',
        ...     properties=AnnotationProperties(
        ...         title='Resource Warning',
        ...         file='disk_check.py',
        ...         startLine=45
        ...     )
        ... )
        '''
        cmd_properties = workflow_cmd.to_command_properties(
            annotation_properties=properties or AnnotationProperties()
        )
        workflow_cmd.issue_command(
            command=WorkflowCommand.WARNING,
            properties=cmd_properties,
            message=str(message)
        )

    @staticmethod
    def error(
        *,
        message: str | Exception,
        properties: AnnotationProperties | None = None
    ) -> None:
        '''
        Write an error message to log.

        This function mirrors error in core.ts. Errors create red
        annotations in the workflow summary.

        Parameters
        ----------
        message : Union[str, Exception]
            Error message or exception.
        properties : Optional[AnnotationProperties]
            Properties to control annotation appearance and location.

        Examples
        --------
        >>> error(message='File not found: data.csv')

        >>> try:
        ...     process_file()
        ... except Exception as e:
        ...     error(
        ...         message=e,
        ...         properties=AnnotationProperties(
        ...             title='Processing Error',
        ...             file='processor.py',
        ...             startLine=102
        ...         )
        ...     )
        '''
        cmd_properties = workflow_cmd.to_command_properties(
            annotation_properties=properties or AnnotationProperties()
        )
        workflow_cmd.issue_command(
            command=WorkflowCommand.ERROR,
            properties=cmd_properties,
            message=str(message)
        )


    @staticmethod
    def start_group(*, name: str) -> None:
        '''
        Begin an output group.

        This function mirrors startGroup in core.ts. Output groups
        create collapsible sections in the workflow logs.

        Parameters
        ----------
        name : str
            Name of the output group.

        See Also
        --------
        end_group : End an output group
        group : Context manager for groups

        Examples
        --------
        >>> start_group(name='Build Dependencies')
        >>> # ... build output ...
        >>> end_group()
        '''
        workflow_cmd.issue(name=WorkflowCommand.GROUP, message=name)

    @staticmethod
    def end_group() -> None:
        '''
        End an output group.

        This function mirrors endGroup in core.ts. Must be called
        after start_group to close the collapsible section.

        See Also
        --------
        start_group : Begin an output group
        group : Context manager for groups

        Examples
        --------
        >>> start_group(name='Test Results')
        >>> # ... test output ...
        >>> end_group()
        '''
        workflow_cmd.issue(name=WorkflowCommand.ENDGROUP)

    @staticmethod
    @contextmanager
    def group(*, name: str) :
        '''
        Context manager for output groups.

        This provides a Pythonic interface for creating collapsible
        log sections, ensuring groups are properly closed.

        Parameters
        ----------
        name : str
            Name of the output group.

        Yields
        ------
        None

        Examples
        --------
        >>> with group(name='Setup Environment'):
        ...     info(message='Installing dependencies...')
        ...     # ... setup code ...
        ...     info(message='Environment ready')
        '''
        ActionLogger.start_group(name=name)
        try:
            yield
        finally:
            ActionLogger.end_group()





