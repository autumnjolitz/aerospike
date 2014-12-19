# -*- coding: utf-8 -*-
import logging
try:
    handler = logging.NullHandler()
except AttributeError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
    handler = NullHandler()

logger = logging.getLogger('aerospike')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
handler.setLevel(logging.DEBUG)
