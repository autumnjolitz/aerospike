# -*- coding: utf-8 -*-
try:
    from .api import (load_library,
                      turn_async_into_sync, rearrange_args_for_tornado)
except ImportError:
    load_library = None
import inspect
try:
    import six
except ImportError:
    six = None
from .constants import DEFAULT_OBJECT_POOL_SIZE, DEFAULT_INITIAL_POOL_SIZE
from .logger import logger
import types
from .cli import gather_cli_options, interpreter


def get_client(
        max_object_pool_size=DEFAULT_OBJECT_POOL_SIZE,
        initial_size=DEFAULT_INITIAL_POOL_SIZE,
        generate_blocking=True, generate_tornado_func_style=True):
    '''
    Secure a client connection.

    A client can pool expensive malloc'ed objects for you.

    if -1 or None, it will never recycle any malloc'ed object.

    generate_blocking: Create blocking versions of async functions
        (denoted by 'bl_' prepended to the functions async name)

    generate_tornado_func_style: Tornado's gen.Task(...) code will call async
        function F like:
            F(args, callback=TORNADO_SPECIAL_CALLBACK)
        This driver expects functions of form: G(callback, arg1, ..., argN)

        generate_tornado_func_style = True means generation of async functions
        that have 't_' prepended to them, where callback is at the end.

        This means you can use things like get_key in a Tornado Request.
    '''
    if not load_library:
        raise ImportError("Unable to import api!")
    initial_size = initial_size or 0
    if initial_size and initial_size < 0:
        initial_size = 0
    if not six:
        raise ImportError("six not installed, broken package?")
    cls = load_library()
    instance = cls(
        initial_object_pool_size=initial_size,
        max_object_pool_size=max_object_pool_size)
    for method in dir(instance):
        func = getattr(instance, method)
        if six.callable(func) and isinstance(func, types.MethodType) \
                and not method.startswith('_') \
                and 'callback' in inspect.getargspec(func).args:
            if generate_blocking and not method.startswith('bl_'):
                setattr(
                    instance, 'bl_' + method,
                    turn_async_into_sync(func))
            if generate_tornado_func_style and not method.startswith('t_'):
                setattr(
                    instance, 't_' + method,
                    rearrange_args_for_tornado(func))
    return instance


def get_logger():
    return logger


def setup_cli():
    from aerospike.common import StateError
    """Entry point for the application script"""
    options = gather_cli_options()
    client = get_client()
    print("Connecting to {0}:{1} for initial cluster discovery...".format(
        options['host'], options['port']))
    client.add_host(options['host'], options['port'])
    interpreter(client)

    try:
        client.shutdown()
    except StateError:
        pass
