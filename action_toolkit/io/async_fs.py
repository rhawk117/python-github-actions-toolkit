from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable
import functools
import inspect
import os
import shutil
from typing import Any, get_type_hints


class AsyncFileSystem:
    '''Async wrapper for file system operations with preserved type hints.'''

    chmod: Callable[..., Awaitable[None]]
    copyfile: Callable[..., Awaitable[str]]
    lstat: Callable[..., Awaitable[os.stat_result]]
    readdir: Callable[..., Awaitable[list[str]]]
    readlink: Callable[..., Awaitable[str]]
    rename: Callable[..., Awaitable[None]]
    stat: Callable[..., Awaitable[os.stat_result]]
    unlink: Callable[..., Awaitable[None]]

    def __init__(self) -> None:
        self._wrap_functions()

    def _wrap_functions(self) -> None:
        '''Wrap common file system functions.'''
        functions_to_wrap = {
            'chmod': os.chmod,
            'copyfile': shutil.copy2,
            'lstat': os.lstat,
            'readdir': os.listdir,
            'readlink': os.readlink,
            'rename': os.rename,
            'stat': os.stat,
            'unlink': os.unlink,
        }

        for name, func in functions_to_wrap.items():
            wrapped = self._create_async_wrapper(func)
            setattr(self, name, wrapped)

    def _create_async_wrapper(self, func: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
        '''Create async wrapper preserving original signature.'''
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        wrapper.__signature__ = sig  # type: ignore
        wrapper.__annotations__ = type_hints.copy()
        if 'return' in wrapper.__annotations__:
            return_type = wrapper.__annotations__['return']
            wrapper.__annotations__['return'] = f'Awaitable[{return_type}]'

        return wrapper




