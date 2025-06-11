from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AnnotationOptions:
    ''''Options for workflow annotations including file location and line details.'''
    title: str | None = field(default=None)
    file: str | Path | None = field(default=None)
    line: int | None = field(default=None)
    endLine: int | None = field(default=None)
    col: int | None = field(default=None)
    endColumn: int | None = field(default=None)

    def get(self) -> dict:
        '''Convert the options to a dictionary for use in GitHub Actions annotations.'''
        return {
            k: v for k, v in asdict(self).items()
            if v is not None
        }





