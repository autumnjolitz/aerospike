# -*- coding: utf-8 -*-
import functools
import six
from .constants import MESSAGES
from .logger import logger
from .common import StateError


def inherit_docstrings(cls):
    '''
    Take a base class and apply it's docstrings to functions
    that do NOT have docstrings.
    '''
    bases = cls.__bases__
    for base_class in bases:
        for member_name in dir(cls):
            member = getattr(cls, member_name)
            if not member_name.startswith('_') and six.callable(member) \
                    and hasattr(base_class, member_name) and not member.__doc__:
                if hasattr(member, '__func__'):
                    member.__func__.__doc__ = \
                        getattr(base_class, member_name).__doc__
    return cls


def override(func):
    '''Call the inherited function first'''
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        getattr(super(self.__class__, self), func.__name__)(*args, **kwargs)
        return func(self, *args, **kwargs)
    return wrapped


def order_call_once(state_type, required_state, new_state=None):
    '''
    Give me a primitive state tracker so I can
    declare the ordering without extra crap.
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            set_state = True
            if self.state[state_type] == required_state:
                try:
                    return func(self, *args, **kwargs)
                except Exception:
                    set_state = False
                    raise
                finally:
                    if set_state and new_state is not None:
                        self.state[state_type] = new_state
            raise StateError(
                MESSAGES['order_call_once_failure'].format(
                    state_type,
                    required_state, self.state[state_type]))
        wrapper.orig_func = func
        return wrapper
    return decorator


def requires(*aerospike_versions):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.version in aerospike_versions:
                return func(self, *args, **kwargs)
            raise NotImplementedError(
                MESSAGES['requires_failure'].format(
                    func.__name__, self.version, aerospike_versions))
        wrapper.min_version = min(aerospike_versions)
        wrapper.orig_func = func
        return wrapper
    return decorator


def warning(version, message):
    '''Print a warning of message if version matches on call'''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.version == version:
                logger.warn(' :: '.join((func.__name__, version, message,)))
            return func(self, *args, **kwargs)
        wrapper.orig_func = func
        return wrapper
    return decorator
