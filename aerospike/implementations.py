# -*- coding: utf-8 -*-
from __future__ import absolute_import
from collections import defaultdict
from .operations import (
    CommonOperations,
    KeyOperations,
    OperatorOperations,
    BatchOperations,
    IndexOperations,
    InfoOperations,
    LargeDataOperations,
    QueryOperations,
    ScanOperations,
    DigestOperations,
    UserDefinedFunctionsOperations,
)
from .common import Base, Constructor


IMPLEMENTED_CLASSES = defaultdict(lambda: [])
IMPLEMENTED_CLASSES['default'].extend(
    [CommonOperations, KeyOperations, OperatorOperations,
     BatchOperations, IndexOperations, InfoOperations,
     LargeDataOperations, QueryOperations, ScanOperations,
     DigestOperations, UserDefinedFunctionsOperations, Base, Constructor])


def order_by_priority(cls_definition):
    '''
    Sort by priority. Classes define priorities if they need
    to be initialized in a specific order.

    In case of the AEROSPIKE 2 LibEvent client, we must
    run the Constructor Class after everything else
    has been init'ed.
    '''
    if hasattr(cls_definition, 'priority'):
        return cls_definition.priority
    return 0


def register(clsname, aerospike_version, library_type):
    IMPLEMENTED_CLASSES[(aerospike_version, library_type)].append(clsname)


def get_implementations(aerospike_version, library_type):
    overriden_classes = IMPLEMENTED_CLASSES[(aerospike_version, library_type,)]
    cls = []
    # Add in default mixins if unimplemented.
    for default_class in IMPLEMENTED_CLASSES['default']:
        class_found = None
        for override in overriden_classes:
            if issubclass(override, default_class):
                class_found = override
                break
        if class_found is None:
            class_found = default_class
        cls.append(class_found)

    # Take all classes that were NOT children
    # of the 'must-be-overriden' classes
    # and add them to the list.
    for override in overriden_classes:
        if override not in cls:
            cls.append(override)

    return sorted(
        cls,
        key=order_by_priority)

# By importing the following implementations,
# this will cause said implementations to register
# with the `implementations' module
from . import implementations_as2libevent
# from . import as2_blocking
# from . import as3_blocking
