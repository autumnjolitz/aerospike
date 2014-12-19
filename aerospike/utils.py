import sys
from ctypes.util import find_library
from .constants import (DEPENDENCY, NONBLOCKING, BLOCKING,
                        AEROSPIKE_3, AEROSPIKE_2,)


class SharedLibrary(object):
    def __init__(self, *names):
        self.names = names

    def __str__(self):
        return 'SharedLibrary({0})'.format(', '.join(self.names))

    def find_library(self):
        for name in self.names:
            dependency = find_library(name)
            if dependency:
                return dependency
        return None

LIBRARY_TYPES = {
    AEROSPIKE_3: [
        DEPENDENCY(SharedLibrary('aerospike'), BLOCKING, [])],
    AEROSPIKE_2: [DEPENDENCY(
        SharedLibrary('ev2citrusleaf-2.0'),
        NONBLOCKING, [SharedLibrary('event', 'event-2.0')]),
        DEPENDENCY(
            SharedLibrary('citrusleaf-2.0'), BLOCKING, [])]
}


def detect_aerospike_libraries(aerospike_version=None):
    """
    Locate Aerospike libraries using ctypes.util.find_library.

    The library that will be used is determined
    by the desired Aerospike capabilities (2 or 3)
    followed by the higher ranked type (i.e. if a NONBLOCKING is
        found, it will win over BLOCKING)

    This function does not depend upon anything and thus is safe to
    call from setup.py.
    """
    aerospike_version = aerospike_version or (AEROSPIKE_2 | AEROSPIKE_3)
    if sys.platform in ('win32', 'cygwin'):
        raise NotImplementedError("Win32 not considered")

    for library_version, potential_libraries in LIBRARY_TYPES.items():
        if library_version & aerospike_version:
            for lib in potential_libraries:
                if lib.shared_object.find_library() and \
                        all([name.find_library() for name in lib.dependencies]):
                    yield library_version, lib
