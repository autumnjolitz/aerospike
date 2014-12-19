# -*- coding: utf-8 -*-

import cffi
from .constants import (DEFINES, MESSAGES, CLASS_NAMES)
from .logger import logger
from .implementations import get_implementations
import os
import six
from .utils import detect_aerospike_libraries
_library = None
import functools
import time
import threading
import inspect

if 'LD_LIBRARY_PATH' in os.environ:
    os.environ['LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH']


def load_library(detected_libraries=None):
    global _library
    if not _library:
        if detected_libraries is None:
            detected_libraries = list(detect_aerospike_libraries())
        if not detected_libraries:
            raise ImportError("Unable to load aerospike libraries!")
        library_depend = sorted(
            detected_libraries,
            key=(lambda tuple: tuple[0]*2 + tuple[1].type), reverse=True)[0]
        _library = generate_interface(*library_depend)
    return _library


class RawLibrary(object):
    '''This is a "magic" class. It will open shared librar(y|ies),
    locate every parsed function from the cdefinitions within them,
    add the references to the top level object (instance of RawLibrary).

    This is so an implementor can call something like:
        self.aerospike_library_func(...)
    without needing to search through arbitrary library properties.
    '''
    def __init__(self, version, dependency, **kwargs):
        ffi = cffi.FFI()
        ffi.cdef(DEFINES[version][dependency.type])
        self._extra_libraries = \
            [ffi.dlopen(lib.find_library()) for lib in dependency.dependencies]
        self._primary_library = ffi.dlopen(
            dependency.shared_object.find_library())
        self._wrapped_cfuncs = set()
        for func_name in (x[9:] for x in ffi._parser._declarations.keys()
                          if x.startswith('function ')):
            try:
                func = getattr(self._primary_library, func_name)
            except AttributeError:
                for library in self._extra_libraries:
                    try:
                        func = getattr(library, func_name)
                    except AttributeError:
                        logger.warn(
                            MESSAGES['disabled_function'].format(
                                dependency.shared_object.find_library(),
                                ', '.join(
                                    str(x) for x in dependency.dependencies),
                                func_name))
                        func = lambda *args: None
                    self._wrapped_cfuncs.add(func_name)
                    setattr(self, func_name, func)
            else:
                setattr(self, func_name, func)
                self._wrapped_cfuncs.add(func_name)
        self.ffi = ffi
        self.version = version
        self.type = dependency.type
        ffi.cdef("void free(void *ptr);")
        # open up LIBC where free lives...
        libc = ffi.dlopen(None)
        # This is needed because sometimes Aerospike
        # does not provide a free function for a call.
        self.free = libc.free
        self._wrapped_cfuncs.add('free')


def rearrange_args_for_tornado(function):
    '''
    Tornado's gen.Task(...) code expects a callback to
    be keyword-specifiable and at the end of the function def.

    We have the opposite form. So use inspect to generate
    named functions with named arguments that have callback as
    a default of None (at the end).

    In order to make the closure reference 'function', we have
    to make a function that defines the true re-arranged function
    that we want.
    '''
    argspec = inspect.getargspec(function)
    original_args = inspect.getargspec(function)
    original_args.args.remove('self')
    fixed_args = argspec.args
    fixed_args.remove('callback')
    fixed_args.remove('self')
    func_def = \
        "def wrapped{0}: return function{1}".format(
            inspect.formatargspec(
                fixed_args + ['callback'], argspec.varargs,
                argspec.keywords,
                (argspec.defaults or ()) + (None,)),
            inspect.formatargspec(*original_args))
    make_fn = None
    func_maker_body = \
        ("def make_fn(function):\n    {0}\n    "
         "return functools.wraps(function)(wrapped)").format(func_def)
    exec(func_maker_body)
    wrapped_func = make_fn(function)
    return wrapped_func


def turn_async_into_sync(function):
    holding_queue = six.moves.queue.Queue()
    wait = threading.Event()
    wait.set()

    def callback(*args):
        holding_queue.put(args)
        wait.clear()

    wrapped_func = functools.partial(function, callback)

    @functools.wraps(function)
    def blocking_function(*args, **kwargs):
        wrapped_func(*args, **kwargs)
        while wait.is_set():
            time.sleep(0.1)
        return holding_queue.get()
    return blocking_function


def generate_interface(version, dependency):
    '''
    Take our loosely ordered list of classes we've implemented
    for, sort it by priority (default 0 if not specified) and
    initialize the library for general public use!
    '''
    class_name = CLASS_NAMES[(version, dependency.type,)]
    mixins = tuple(
        [RawLibrary] + get_implementations(
            version, dependency.type))

    class_interface = type(
        class_name,
        mixins,
        {})
    logger.debug("Mixins requested: {0}".format(mixins))

    def __init__(self, *args, **kwargs):
        # initialize all mixin inits
        for cls in mixins:
            if cls.__init__ == object.__init__:
                continue
            logger.debug("Initializing {0}".format(cls.__name__))
            cls.__init__(self, version, dependency, *args, **kwargs)

    class_interface.__init__ = __init__
    return class_interface
