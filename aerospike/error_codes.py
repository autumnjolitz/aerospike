# -*- coding: utf-8 -*-
class AerospikeError(ValueError):
    pass

FORMAT = "Error Type: {0}, Message: {1}"
EV2CITRUSLEAF_OK = 0

AEROSPIKE2_NONBLOCKING = {
    -1: ("EV2CITRUSLEAF_FAIL_CLIENT_ERROR",
         " Out of memory or similar error"),
    -2: ("EV2CITRUSLEAF_FAIL_TIMEOUT",
         "Time expired before operation completed"),
    -3: ("EV2CITRUSLEAF_FAIL_THROTTLED",
         "Async communication buffer full"),
    1: ("EV2CITRUSLEAF_FAIL_UNKNOWN",
        "Unknown failure on the server side"),
    2: ("EV2CITRUSLEAF_FAIL_NOTFOUND",
        "Key not found in database"),
    3: ("EV2CITRUSLEAF_FAIL_GENERATION",
        "Generation mismatch"),
    4: ("EV2CITRUSLEAF_FAIL_PARAMETER",
        "Caller passed in bad parameters"),
    5: ("EV2CITRUSLEAF_FAIL_KEY_EXISTS",
        "Cannot replace key – check unique parameter"),
    6: ("EV2CITRUSLEAF_FAIL_BIN_EXISTS",
        " Cannot overwrite bin – check unique_bin parameter"),
    7: ("EV2CITRUSLEAF_FAIL_CLUSTER_KEY_MISMATCH",
        "Cluster key mismatch"),
    8: ("EV2CITRUSLEAF_FAIL_PARTITION_OUT_OF_SPACE",
        "Partition out of space"),
    9: ("EV2CITRUSLEAF_FAIL_SERVERSIDE_TIMEOUT",
        "Server timeout expired"),
    10: ("EV2CITRUSLEAF_FAIL_NOXDS",
         "Cross Data Replication (XDR) error"),
    11: ("EV2CITRUSLEAF_FAIL_UNAVAILABLE",
         "Node unavailable"),
    12: ("EV2CITRUSLEAF_FAIL_INCOMPATIBLE_TYPE",
         "Operation cannot be applied to that type"),
    13: ("EV2CITRUSLEAF_FAIL_RECORD_TOO_BIG",
         "Record too big"),
    14: ("EV2CITRUSLEAF_FAIL_KEY_BUSY",
         "Key locked by another"),
}


def aerospike_2_non_blocking_raise_error(code):
    if code in AEROSPIKE2_NONBLOCKING:
        raise AerospikeError(FORMAT.format(*AEROSPIKE2_NONBLOCKING[code]))
    return


def aerospike_2_non_blocking_format_error(code):
    return FORMAT.format(*AEROSPIKE2_NONBLOCKING[code])
