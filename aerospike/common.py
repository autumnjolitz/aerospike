# -*- coding: utf-8 -*-
import uuid
from .logger import logger
from six.moves import range as xrange
from collections import defaultdict
import abc
import time


class ObjectPool(object):
    DEFAULT_CAPACITY = 1000
    IDENTITY = lambda x: x

    def __init__(self, max_capacity=DEFAULT_CAPACITY):
        self._available_pool = defaultdict(lambda: [])
        self._available_pool_counters = defaultdict(lambda: 0)
        self.max_capacity = max_capacity

    def checkin(self, type, obj, clean_func=IDENTITY):
        if self.max_capacity > self._available_pool_counters[type]:
            clean_func(obj)
            self._available_pool[type].append(obj)
            self._available_pool_counters[type] += 1
        return None

    def checkout(self, type, object_creation_func,
                 object_creation_func_args=None):
        obj = None
        try:
            obj = self._available_pool[type].pop()
        except IndexError:
            if object_creation_func_args:
                obj = object_creation_func(*object_creation_func_args)
            else:
                obj = object_creation_func()
        else:
            self._available_pool_counters[type] -= 1
        return obj


class Constructor(object):
    __metaclass__ = abc.ABCMeta
    priority = float('inf')

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        '''
        This is the logic for instantiating a live client.

        Set up the event loop, etc,.
        '''

    @abc.abstractmethod
    def shutdown(self):
        '''
        All clients must have the ability to shutdown and clean themselves up.
        '''


class Base(object):
    __metaclass__ = abc.ABCMeta
    priority = -1

    def __init__(self, *args, **kwargs):
        self.state = defaultdict(lambda: 0)
        # mapping of uid -> (callback, [references_to_hold_until_completed])
        self.unique_ids_available = []
        self.outstanding_calls = {}
        self.generic_pool = ObjectPool()
        self.bigint = 1
        self.outstanding_total = 0

        self.num_unique_ids_available = 0
        # prefill the uniq_id pool if desired:
        for i in xrange(0, kwargs['initial_object_pool_size']):
            self.unique_ids_available.append(self.__generate_uuid())
        self.num_unique_ids_available = len(self.unique_ids_available)
        self.max_object_pool_size = \
            kwargs.get('max_object_pool_size', float('inf'))
        self._on = True

    def _async_checkin(self, callback, refs_to_hold):
        '''
        Return void* of a unique id.

        This is a special case, as we use this to hold onto C-value references
        from Garbage Collection until the uuid returns to us.

        Use the generic_pool for everything else!

        Try to grab from the object pool first before malloc'ing
        a new c string and making a cast to (void*).
        '''
        uid = cuid = void_ptr = None
        if self.num_unique_ids_available:
            try:
                uid, cuid, void_ptr = self.unique_ids_available.pop()
            except IndexError:
                if self.max_object_pool_size < float('inf') and self._on:
                    # self._pause_event_loop()
                    # self._on = False
                    pass
            else:
                self.num_unique_ids_available -= 1
        if uid is None:
            uid, cuid, void_ptr = self.__generate_uuid()
        self.outstanding_calls[uid] = (callback, refs_to_hold, cuid, void_ptr)
        self.outstanding_total += 1
        return void_ptr

    def __generate_uuid(self):
        self.bigint += 1
        uid = str(self.bigint).encode('utf8')
        cuid = self.ffi.new('char[]', uid)
        void_ptr = self.ffi.cast('void *', cuid)
        return uid, cuid, void_ptr

    def _async_complete(self, uid):
        '''
        Return the callback and the references being held to avoid a GC.

        Check the unique id back into the pool for re-use later to
        avoid an expensive malloc.
        '''
        try:
            callback, refs_to_hold, cuid, void_ptr = \
                self.outstanding_calls.pop(uid)
        except KeyError:
            logger.exception(
                ("Fatal fault in _handle_callback. "
                 "Unable to find uid {0}").format(uid))
        else:
            self.outstanding_total -= 1
            # if self.outstanding_total < 700:
            #     self._resume_event_loop()
            #     self._on = True
            if self.num_unique_ids_available < self.max_object_pool_size:
                self.unique_ids_available.append((uid, cuid, void_ptr,))
                self.num_unique_ids_available += 1
            return callback, refs_to_hold
        return None

    @abc.abstractmethod
    def _get_log_level(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _set_log_level(self, level):
        raise NotImplementedError

    def get_log_level(self):
        '''Get the C Library logging level.
        By default it should be set to not log anything'''
        return self._get_log_level()

    def set_log_level(self, level):
        '''Set the C Library logging level.'''
        return self._set_log_level(level)

    log_level = property(
        get_log_level, set_log_level)


class StateError(Exception):
    pass

# possibility of object pooling?
# def check_out(ffi, ctype):
#     try:
#         oldobj = CACHE[ctype].pop()
#     except (KeyError, IndexError):
#         return ffi.new(ctype)
