'''
GitHub Actions job summary functionality.

This module provides the Summary class for creating markdown summaries
that appear in the GitHub Actions workflow summary page. Mirrors the
summary functionality in @actions/core.
'''

from __future__ import annotations
import os
from pathlib import Path

from io import StringIO
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from action_toolkit.core.internals.exceptions import CoreActionError

if TYPE_CHECKING:
    from typing import Any, IO


class SummaryWriter(ABC):
    '''Abstract base class for summary writers.'''

    @abstractmethod
    def write(self, content: str) -> None:
        '''Write content to the summary.'''
        pass

    @abstractmethod
    def clear(self) -> None:
        '''Clear the summary content.'''
        pass


class FileSummaryWriter(SummaryWriter):
    '''File-based summary writer.'''

    def __init__(self, file_path: str) -> None:
        '''Initialize with the summary file path.'''
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, content: str) -> None:
        '''Append content to the summary file.'''
        with open(self.file_path, 'a', encoding='utf-8') as f:
            f.write(content)

    def clear(self) -> None:
        '''Clear the summary file.'''
        if self.file_path.exists():
            self.file_path.unlink()


class Summary:
    '''
    GitHub Actions job summary builder.

    This class mirrors the Summary class in @actions/core, providing
    a fluent API for building markdown summaries that appear in the
    GitHub Actions UI.

    The summary supports GitHub Flavored Markdown (GFM) including:
    - Headers, paragraphs, and line breaks
    - Bold, italic, and code formatting
    - Links and images
    - Lists (ordered and unordered)
    - Tables
    - Code blocks with syntax highlighting
    - Quotes and details/summary sections

    Examples
    --------
    >>> summary = Summary()
    >>> (summary
    ...     .add_heading('Test Results')
    ...     .add_paragraph('All tests passed!')
    ...     .add_table([
    ...         ['Test', 'Status', 'Time'],
    ...         ['test_foo', '✅ Passed', '1.2s'],
    ...         ['test_bar', '✅ Passed', '0.8s']
    ...     ])
    ...     .write())
    '''

    def __init__(self, writer: SummaryWriter | None = None) -> None:
        '''
        Initialize a new Summary instance.

        Parameters
        ----------
        writer : Optional[SummaryWriter]
            Custom writer for testing. Defaults to file writer using
            GITHUB_STEP_SUMMARY environment variable.
        '''
        if writer is None:
            summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
            if not summary_path:
                raise CoreActionError(
                    'GITHUB_STEP_SUMMARY environment variable is not set. '
                    'This API is only available in GitHub Actions.'
                )
            writer = FileSummaryWriter(summary_path)

        self._writer = writer
        self._buffer = StringIO()
        self._file_path = (
            self._writer.file_path if hasattr(self._writer, 'file_path')
            else None
        )

    def write(self, *, overwrite: bool = False) -> 'Summary':
        '''
        Write the summary buffer to the summary file.

        Parameters
        ----------
        overwrite : bool
            Whether to overwrite existing content. Default appends.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        if overwrite:
            self._writer.clear()

        content = self._buffer.getvalue()
        if content:
            self._writer.write(content)
            self._buffer = StringIO()

        return self

    def clear(self) -> 'Summary':
        '''
        Clear both the buffer and the summary file.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        self._buffer = StringIO()
        self._writer.clear()
        return self

    def stringify(self) -> str:
        '''
        Get the current buffer content as a string.

        Returns
        -------
        str
            The markdown content in the buffer.
        '''
        return self._buffer.getvalue()

    def is_empty(self) -> bool:
        '''
        Check if the buffer is empty.

        Returns
        -------
        bool
            True if buffer has no content.
        '''
        return self._buffer.tell() == 0

    def add_raw(self, text: str, *, add_eol: bool = False) -> 'Summary':
        '''
        Add raw text to the summary.

        Parameters
        ----------
        text : str
            Raw text to add.
        add_eol : bool
            Whether to add a newline. Default False.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        self._buffer.write(text)
        if add_eol:
            self._buffer.write(os.linesep)
        return self

    def add_eol(self) -> 'Summary':
        '''
        Add an end-of-line character.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        return self.add_raw(os.linesep)

    def add_heading(self, text: str, *, level: int = 1) -> 'Summary':
        '''
        Add a markdown heading.

        Parameters
        ----------
        text : str
            The heading text.
        level : int
            Heading level (1-6). Default 1.

        Returns
        -------
        Summary
            Self for chaining.

        Raises
        ------
        ValueError
            If level is not between 1 and 6.
        '''
        if not 1 <= level <= 6:
            raise ValueError(f'Heading level must be 1-6, got {level}')

        prefix = '#' * level
        return self.add_raw(f'{prefix} {text}', add_eol=True).add_eol()

    def add_paragraph(self, text: str) -> 'Summary':
        '''
        Add a paragraph with proper spacing.

        Parameters
        ----------
        text : str
            The paragraph text.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        return self.add_raw(text, add_eol=True).add_eol()

    def add_text(self, text: str) -> 'Summary':
        '''
        Add text without additional formatting.

        Parameters
        ----------
        text : str
            The text to add.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        return self.add_raw(text)

    def add_code_block(
        self,
        code: str,
        *,
        lang: str | None = None
    ) -> 'Summary':
        '''
        Add a fenced code block with optional syntax highlighting.

        Parameters
        ----------
        code : str
            The code content.
        lang : Optional[str]
            Language for syntax highlighting (e.g., 'python', 'javascript').

        Returns
        -------
        Summary
            Self for chaining.
        '''
        lang_spec = lang or ''
        return (
            self.add_raw(f'```{lang_spec}', add_eol=True)
            .add_raw(code, add_eol=True)
            .add_raw('```', add_eol=True)
            .add_eol()
        )

    def add_list(
        self,
        items: list[str | list[str]],
        *,
        ordered: bool = False
    ) -> 'Summary':
        '''
        Add a list (ordered or unordered).

        Parameters
        ----------
        items : List[Union[str, List[str]]]
            List items. Nested lists are supported.
        ordered : bool
            Whether to create an ordered list. Default False.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        def render_items(items: list[str | list[str]], depth: int = 0) -> None:
            indent = '  ' * depth
            for i, item in enumerate(items, 1):
                if isinstance(item, list):
                    render_items(item, depth + 1)
                else:
                    marker = f'{i}.' if ordered and depth == 0 else '-'
                    self.add_raw(f'{indent}{marker} {item}', add_eol=True)

        render_items(items)
        return self.add_eol()

    def add_table(self, rows: list[list[str]]) -> 'Summary':
        '''
        Add a markdown table.

        Parameters
        ----------
        rows : List[List[str]]
            Table rows. First row is treated as headers.

        Returns
        -------
        Summary
            Self for chaining.

        Raises
        ------
        ValueError
            If table has no rows or inconsistent columns.
        '''
        if not rows:
            raise ValueError('Table must have at least one row')

        col_count = len(rows[0])
        if any(len(row) != col_count for row in rows):
            raise ValueError('All rows must have the same number of columns')

        self.add_raw('| ' + ' | '.join(rows[0]) + ' |', add_eol=True)

        self.add_raw('|' + '|'.join([' --- ' for _ in range(col_count)]) + '|', add_eol=True)

        for row in rows[1:]:
            self.add_raw('| ' + ' | '.join(row) + ' |', add_eol=True)

        return self.add_eol()

    def add_details(
        self,
        label: str,
        content: str
    ) -> 'Summary':
        '''
        Add a collapsible details section.

        Parameters
        ----------
        label : str
            The summary label (always visible).
        content : str
            The details content (collapsible).

        Returns
        -------
        Summary
            Self for chaining.
        '''
        return (
            self.add_raw('<details>', add_eol=True)
            .add_raw(f'<summary>{label}</summary>', add_eol=True)
            .add_eol()
            .add_raw(content, add_eol=True)
            .add_eol()
            .add_raw('</details>', add_eol=True)
            .add_eol()
        )

    def add_image(
        self,
        src: str,
        alt: str,
        *,
        title: str | None = None,
        width: int | None = None,
        height: int | None = None
    ) -> 'Summary':
        '''
        Add an image.

        Parameters
        ----------
        src : str
            Image source URL.
        alt : str
            Alternative text for the image.
        title : Optional[str]
            Image title (tooltip).
        width : Optional[int]
            Image width in pixels.
        height : Optional[int]
            Image height in pixels.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        img_tag = f'<img src="{src}" alt="{alt}"'

        if title:
            img_tag += f' title="{title}"'
        if width:
            img_tag += f' width="{width}"'
        if height:
            img_tag += f' height="{height}"'

        img_tag += '>'

        return self.add_raw(img_tag, add_eol=True).add_eol()

    def add_separator(self) -> 'Summary':
        '''
        Add a horizontal separator.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        return self.add_raw('---', add_eol=True).add_eol()

    def add_break(self) -> 'Summary':
        '''
        Add a line break.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        return self.add_raw('<br>', add_eol=True)

    def add_quote(self, text: str, *, cite: str | None = None) -> 'Summary':
        '''
        Add a block quote.

        Parameters
        ----------
        text : str
            The quote text.
        cite : Optional[str]
            Citation for the quote.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        lines = text.strip().split('\n')
        for line in lines:
            self.add_raw(f'> {line}', add_eol=True)

        if cite:
            self.add_raw(f'> — {cite}', add_eol=True)

        return self.add_eol()

    def add_link(self, text: str, href: str) -> 'Summary':
        '''
        Add an inline link.

        Parameters
        ----------
        text : str
            Link text.
        href : str
            Link URL.

        Returns
        -------
        Summary
            Self for chaining.
        '''
        return self.add_raw(f'[{text}]({href})')


summary = Summary()

markdownSummary = summary
__all__ = [
    'Summary',
    'SummaryWriter',
    'FileSummaryWriter',
    'summary',
    'markdownSummary'
]