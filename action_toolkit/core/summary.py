"""
**core.summary**
GitHub Actions job summary functionality.

This module provides the Summary class for creating markdown summaries
that appear in the GitHub Actions workflow summary page. Mirrors the
summary functionality in @actions/core.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Final, Self


@dataclasses.dataclass(frozen=True, slots=True)
class SummaryTableRow:
    data: str
    header: bool = False
    colspan: str = '1'
    rowspan: str = '1'


SUMMARY_ENV: Final[str] = 'GITHUB_STEP_SUMMARY'


def resolve_summary_path() -> Path:
    global SUMMARY_ENV
    file_path = os.getenv(SUMMARY_ENV)
    if not file_path:
        raise RuntimeError(
            f'Environment variable {SUMMARY_ENV} is not set. '
            'Ensure you are running in a GitHub Actions environment that supports summaries.'
        )
    path = Path(file_path)

    try:
        path.read_text()
    except Exception:
        raise RuntimeError(
            f'Failed to read summary file at {path}. '
            'Ensure the file exists and is accessible.'
        )

    return path


class Summary:
    '''
    Almost identical to the TypeScript implementation for the time being,
    definitely not fully implemented or the most "pythonic" way to do this.
    '''

    def __init__(self, overwrite: bool = False) -> None:
        """Initialize the summary with an empty StringIO buffer."""
        self._buffer = ''
        self._file_path: Path = resolve_summary_path()
        self._overwrite = overwrite

    def _wrap(
        self,
        tag: str,
        content: str | None,
        attrs: dict[str, str] = {}
    ) -> str:
        """Wrap content in a markdown tag."""
        if content is None:
            return ''
        html_attrs = ' '.join(
            f'{k}="{v}"' for k, v in attrs.items() if v
        )
        if not content:
            return f'<{tag} {html_attrs}>'

        return f'<{tag} {html_attrs}>{content}</{tag}>'

    def write(self) -> Self:
        path = self._file_path
        if not path.is_file():
            raise RuntimeError(
                f'Summary file {path} does not exist. '
                'Ensure you are running in a GitHub Actions environment that supports summaries.'
            )
        if self._overwrite:
            path.write_text(self._buffer, encoding='utf-8')
        else:
            with path.open('a', encoding='utf-8') as f:
                f.write(self._buffer)
        return self.empty()

    def empty(self) -> Self:
        """Clear the summary content."""
        self._buffer = ''
        return self

    def append_text(self, text: str, add_sep: bool = False) -> Self:
        """Append plain text to the summary."""
        self._buffer += text
        if add_sep:
            self._buffer += os.linesep
        return self

    def add_code_block(
        self,
        code: str,
        lang: str | None = None,
    ) -> Self:
        """Add a code block to the summary."""

        attrs = {'lang': lang} if lang else {}

        element = self._wrap('pre', self._wrap('code', code, attrs))

        return self.append_text(element, add_sep=True)

    def add_list(
        self,
        items: list[str],
        ordered: bool = False,
    ) -> Self:
        """Add a list to the summary."""
        tag = 'ol' if ordered else 'ul'
        content = ''.join(f'<li>{item}</li>' for item in items)
        element = self._wrap(tag, content)
        return self.append_text(element, add_sep=True)

    def add_table(self, rows: list[SummaryTableRow]) -> Self:
        """Add a table to the summary."""
        if not rows:
            return self

        tags = []
        for row in rows:
            if isinstance(row, str):
                tags.append(self._wrap('td', row))

            elif isinstance(row, SummaryTableRow):
                tag = 'th' if row.header else 'td'
                attrs = {
                    'colspan': row.colspan,
                    'rowspan': row.rowspan
                }
                content = self._wrap(tag, row.data, attrs)
                tags.append(self._wrap('tr', content))

        content = ''.join(tags)

        return self.append_text(self._wrap('table', content), add_sep=True)

    def add_details(
        self,
        summary: str,
        content: str,
    ) -> Self:
        """Add a details block to the summary."""
        details = self._wrap('details', self._wrap(
            'summary', summary) + content)
        return self.append_text(details, add_sep=True)

    def add_heading(
        self,
        text: str,
        level: int | str = 1,
    ) -> Self:
        """Add a heading to the summary."""
        tag = f'h{level}'
        return self.append_text(self._wrap(tag, text), add_sep=True)

    def add_seperator(
        self,
    ) -> Self:
        """Add a horizontal rule or separator to the summary."""
        return self.append_text(
            '<hr />',
            add_sep=True
        )

    def add_break(
        self,
    ) -> Self:
        """Add a line break to the summary."""
        return self.append_text('<br />', add_sep=True)

    def add_quote(
        self,
        text: str,
        cite: str | None = None
    ) -> Self:
        """Add a blockquote to the summary."""
        attrs = {}
        if cite:
            attrs['cite'] = cite

        return self.append_text(self._wrap('blockquote', text, attrs), add_sep=True)

    def add_link(
        self,
        text: str,
        url: str
    ) -> Self:
        """Add a hyperlink to the summary."""
        return self.append_text(
            self._wrap('a', text, {'href': url}),
            add_sep=True
        )


__all__ = [
    'Summary',
    'SummaryTableRow'
]
