"""
**exec.interfaces**

Pythonic interfaces for command execution with enhanced options.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from action_toolkit.corelib.types.io import StringOrPathlib
