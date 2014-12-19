# -*- coding: utf-8 -*-
'''A Dispatcher is the interface for submitting queries to the
C backend in an ordered manner. These are meant to be used as
Mixins.
'''
import time
from six.moves import queue as Queue
import threading
import abc
from .logger import logger
from .decorators import order_call_once
from functools import partial
from .constants import MESSAGES


class AsyncDispatcherStates(object):
    UNINITIALIZED = 0
    INITIALIZED = 1
    RUNNING = 2

order_call_once = partial(order_call_once, AsyncDispatcherStates)


class AsyncDispatcher(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.state[AsyncDispatcher] = AsyncDispatcherStates.UNINITIALIZED

    def _pause_event_loop(self):
        pass

    def _resume_event_loop(self):
        pass

    @abc.abstractmethod
    def _setup_async(self):
        '''
        Setup the necessary objects to allow non-blocking operations
        '''
        pass

    @abc.abstractmethod
    def _destruct_async(self):
        '''Destruct what setup made'''
        pass

    @abc.abstractmethod
    def _activate_loop(self):
        '''
        If we need to start running threads/event loops, do it now.
        '''
        pass

    @abc.abstractmethod
    def _deactivate_loop(self):
        '''Perform the necessary shutdown/cleanup sequence to
        stop the nonblocking calls'''
        pass

    @abc.abstractmethod
    def _submit_work(self, function_ptr, *args):
        '''In case of the event loop, we'd just call the
        non blocking function_ptr(*args).

        But in case of the threading shim, we'd have to submit
        the function_ptr and arguments to a queue.
        '''
        pass


class LibEvent(AsyncDispatcher):
    '''
    LibEvent rarely (if ever) changes, so I expect this
    to be a stable API.
    '''
    def __init__(self, *args, **kwargs):
        super(LibEvent, self).__init__()
        self._event_loop_thread = None
        self._event_loop = None
        self._event_loop_queue = None
        self._event_loop_running_toggle = None
        self.is_full = threading.Event()

    @order_call_once(
        AsyncDispatcherStates.UNINITIALIZED,
        new_state=AsyncDispatcherStates.INITIALIZED)
    def _setup_async(self):
        loop = self.event_base_new()
        # if libevent was compiled with pthreads,
        # this will instruct it to place additional locks
        # in place. I doubt this is needed though, since
        # we halt the event loop, add work, then begin it again.
        self.evthread_use_pthreads()
        self.evthread_make_base_notifiable(loop)

        self._event_loop = loop
        self._event_loop_queue = Queue.Queue()
        self._event_loop_running_toggle = threading.Event()

    def _pause_event_loop(self):
        # print('pausing')
        self.is_full.set()

    def _resume_event_loop(self):
        # print('resuming')
        self.is_full.clear()

    @order_call_once(
        AsyncDispatcherStates.INITIALIZED,
        new_state=AsyncDispatcherStates.INITIALIZED |
        AsyncDispatcherStates.RUNNING)
    def _activate_loop(self):
        '''
        CFFI releases the GIL. So we can treat the event_loop
        like an IO operation that never returns (thus never blocking
            the main thread).
        We do this to avoid the double dealloc error in Aerospike from calling
        into an active loop.
        '''
        thread_queue = self._event_loop_queue
        evt = self._event_loop_running_toggle
        is_full = self.is_full
        is_full.clear()

        def run_loop():
            logger.debug("Starting Event Loop")
            evt.set()
            code = 0
            while evt.is_set():
                while not is_full.is_set() and not thread_queue.empty():
                    try:
                        func_ptr, args = thread_queue.get_nowait()
                    except Queue.Empty:
                        break
                    else:
                        code = func_ptr(*args)
                        if code:
                            if code in (-1, -3):
                                if code == -1:
                                    logger.critical(
                                        "Unable to generate network request"
                                        " on event loop.")
                                else:
                                    logger.critical("Connection throttled.")
                                thread_queue.put_nowait((func_ptr, args,))
                            else:
                                logger.info("Unknown code {0}".format(code))
                            break
                code = self.event_base_loop(self._event_loop, 0x01)
                if code == -1:
                    logger.critical(
                        MESSAGES['event_loop_in_trouble'].format(code))

        t = threading.Thread(target=run_loop, args=())
        t.daemon = True
        self._event_loop_thread = t
        t.start()

    @order_call_once(
        AsyncDispatcherStates.INITIALIZED | AsyncDispatcherStates.RUNNING)
    def _submit_work(self, function_ptr, *args):
        self._event_loop_queue.put_nowait((function_ptr, args,))
        # self.event_base_loopexit(self._event_loop, self.ffi.NULL)

    @order_call_once(
        AsyncDispatcherStates.INITIALIZED | AsyncDispatcherStates.RUNNING,
        new_state=AsyncDispatcherStates.INITIALIZED)
    def _deactivate_loop(self):
        self._event_loop_running_toggle.clear()
        # self.event_base_loopbreak(self._event_loop)
        self._event_loop_thread = None

    @order_call_once(
        AsyncDispatcherStates.INITIALIZED,
        new_state=AsyncDispatcherStates.UNINITIALIZED)
    def _destruct_async(self):
        self.event_base_free(self._event_loop)
        self._event_loop = None
        self._event_loop_queue = None
        self._event_loop_running_toggle = None


class PThreader(AsyncDispatcher):
    def __init__(self):
        super(PThreader, self).__init__()
