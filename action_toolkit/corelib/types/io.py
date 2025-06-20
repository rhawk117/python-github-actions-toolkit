"""
**io**
File system and path related types.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any, TypeAlias

OSFilePath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]
IOValue: TypeAlias = str | int | float | bool | dict[str, Any]
StringOrPathlib: TypeAlias = str | Path
