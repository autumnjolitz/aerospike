# -*- coding: utf-8 -*-
import os
from collections import namedtuple
DEFAULT_OBJECT_POOL_SIZE = 4096
DEFAULT_INITIAL_POOL_SIZE = 1024
DEFAULT_TIMEOUT_MS = 1000

DEPENDENCY = namedtuple("DEPENDENCY", "shared_object type dependencies")
NONBLOCKING = 1
BLOCKING = 0
AEROSPIKE_3 = 3
AEROSPIKE_2 = 2

AEROSPIKE_2_NONBLOCKING_HEADERS = "as2nb.h"

CLASS_NAMES = {
    (AEROSPIKE_2, NONBLOCKING): "Aerospike2Nonblocking"
}

this_dir = os.path.dirname(os.path.abspath(__file__))
MESSAGES = {
    'disabled_function': ("Unable to detect function "
                          "{2} in {0} or {1}. Setting as NotImplemented"),
    'order_call_once_failure': (
        "You cannot call this function! Type: {0}, Required State: {1}, "
        "Current State: {2}"),
    'requires_failure': (
        "{0} not available in Aerospike {1}, but appears"
        " in Aerospike version(s): {2}"),
    'event_loop_in_trouble': "EVENT LOOP TERMINATED ABNORMALLY, code {0}"
}


def read(fn):
    with open(os.path.join(this_dir, fn), 'r') as fh:
        content = fh.read()
    return content

DEFINES = {
    AEROSPIKE_3: {
        BLOCKING: """
        """
    },
    AEROSPIKE_2: {
        BLOCKING: """
        """,
        NONBLOCKING: read(AEROSPIKE_2_NONBLOCKING_HEADERS)
    }
}
