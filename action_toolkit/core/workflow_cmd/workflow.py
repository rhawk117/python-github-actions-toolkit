from pathlib import Path
import sys
from typing import IO, ClassVar

from .params import AnnotationOptions


class WorkflowCommand:
    """A wrapper class for writing GitHub Actions commands to the output stream."""

    _ENCODING_MAP: ClassVar[dict[str, str]] = {'%': '%25', '\r': '%0D', '\n': '%0A'}

    def __init__(self, *, debug_enabled: bool = False) -> None:
        self.debug_enabled: bool = debug_enabled

    def encode(self, text: str | Path) -> str:
        """Percent-encode %, CR and LF as required by the spec."""
        if isinstance(text, Path):
            text = str(text)
        for char, repl in self._ENCODING_MAP.items():
            text = text.replace(char, repl)
        return text

    def emit_stream(
        self,
        command_name: str,
        *,
        value: str = '',
        stream: IO[str] = sys.stdout,
        options: AnnotationOptions | dict | None = None,
    ) -> None:
        """Write the final '::<command> <k=v,…>::<value>' string."""
        if not options:
            options = {}
        elif isinstance(options, AnnotationOptions):
            options = options.get()

        options_str = ','.join(
            f'{key}={self.encode(str(value))}' for key, value in options.items() if value is not None
        )
        if options_str:
            options_str = f' {options_str}'
        encoded_value = self.encode(value)
        print(f'::{command_name}{options_str}::{encoded_value}', file=stream, flush=True)

    @classmethod
    def emit(
        cls,
        command_name: str,
        value: str = '',
        *,
        stream: IO[str] = sys.stdout,
        options: AnnotationOptions | dict | None = None,
        debug_enabled: bool = False,
    ) -> None:
        """Emit a command with the given name and options."""
        cmd = cls(debug_enabled=debug_enabled)
        cmd.emit_stream(command_name, value=value, options=options, stream=stream)

    @classmethod
    def get_set_options(cls, options: AnnotationOptions | dict | None = None) -> dict[str, str]:
        """Get options as a dictionary for setting in the command."""
        if options is None:
            return {}
        elif isinstance(options, AnnotationOptions):
            options = options.get()
        return {key: cls().encode(str(value)) for key, value in options.items() if value}
