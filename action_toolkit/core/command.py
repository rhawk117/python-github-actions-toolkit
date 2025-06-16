'''
Command issuing functionality for GitHub Actions.

This module provides the low-level command formatting and issuing functionality
that mirrors the @actions/core command.ts implementation.
'''

from __future__ import annotations
from typing import TYPE_CHECKING

import json
import os
import sys

if TYPE_CHECKING:
    from .types import CommandValue, CommandPropertyValue, WorkflowCommand
    from typing import Literal, TextIO, Any, Final

CMD_STRING: Final[str] = '::'





