'''
**io**
File system operations for GitHub Actions.

This module provides cross-platform file operations including copy, move,
delete, and executable finding functionality.
'''

from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass
from . import io_utils

