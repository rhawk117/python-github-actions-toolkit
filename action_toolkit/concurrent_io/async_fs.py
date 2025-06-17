'''
**async_fs.py** - Async wrapper for file system operations with preserved type hints.


'''
from __future__ import annotations
import asyncio
import functools
import inspect
import os
import shutil
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, get_type_hints

P = ParamSpec('P')
R = TypeVar('R')

def asyncify(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    '''Converts a synchronous function to an asynchronous one using
    asyncio.to_thread

    Parameters
    ----------
    func : Callable[P, R]
        _the original function_

    Returns
    -------
    Callable[P, Awaitable[R]]
        _the async wrapped function_
    '''

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        event_loop = asyncio.get_event_loop()
        return await event_loop.run_in_executor(
            None,
            lambda: func(*args, **kwargs)
        )

    wrapper.__signature__ = inspect.signature(func)  # type: ignore
    wrapper.__annotations__ = get_type_hints(func).copy()
    if 'return' in wrapper.__annotations__:
        return_type = wrapper.__annotations__['return']
        wrapper.__annotations__['return'] = f'Awaitable[{return_type}]'

    return wrapper

_WRAPPED_OS_FUNCS = {
    'chmod': os.chmod,
    'copyfile': shutil.copy2,
    'lstat': os.lstat,
    'readdir': os.listdir,
    'readlink': os.readlink,
    'rename': os.rename,
    'stat': os.stat,
    'unlink': os.unlink
}




_async_chmod = asyncify(os.chmod)
_async_copyfile = asyncify(shutil.copy2)
_async_lstat = asyncify(os.lstat)
_async_readdir = asyncify(os.listdir)
_async_readlink = asyncify(os.readlink)
_async_rename = asyncify(os.rename)
_async_stat = asyncify(os.stat)
_async_unlink = asyncify(os.unlink)



