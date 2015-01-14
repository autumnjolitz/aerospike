# -*- coding: utf-8 -*-
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
from .data_types import (Digest)
from .implementations import register
from . import constants
from .constants import DEFAULT_TIMEOUT_MS
from .dispatchers import LibEvent, AsyncDispatcherStates
from .decorators import order_call_once, inherit_docstrings
from .common import StateError, Base, Constructor
from . import filters
from . import error_codes
from .logger import logger
import six
from six.moves import range as xrange


def coerce_bytes_py2(iterable):
    return bytes(bytearray(iterable))


def coerce_bytes_py3(iterable):
    return bytes(iterable)

if six.PY2:
    coerce_bytes = coerce_bytes_py2
elif six.PY3:
    coerce_bytes = coerce_bytes_py3

VERSION = (constants.AEROSPIKE_2, constants.NONBLOCKING)
CHECKIN_OBJ_FAILURE = \
    "Object checked into {0} pool is not correct type!"
EV2CALLBACK = \
    ("void(*)(int return_value,  ev2citrusleaf_bin *bins, "
     "int n_bins, uint32_t generation, uint32_t expiration, "
     "void *udata )")


class AS2CommonStates(object):
    UNINITIALZED = 0
    INITIALIZED = 1


@inherit_docstrings
class AS2CommonOperations(CommonOperations):
    def __init__(self, *args, **kwargs):
        self.state[AS2CommonStates] = AS2CommonStates.UNINITIALZED
        self._static_opts = self.ffi.new(
            "ev2citrusleaf_cluster_static_options *")
        self._static_opts.cross_threaded = True

        self._options = self.ffi.new(
            'ev2citrusleaf_cluster_runtime_options *')
        self._options.socket_pool_max = 1000
        self._options.read_master_only = False
        self._options.throttle_reads = False
        self._options.throttle_writes = False
        self._options.throttle_threshold_failure_pct = 2
        self._options.throttle_window_seconds = 15
        self._options.throttle_factor = 10
        self._cluster = None
        self._hosts = set()

    @property
    def hosts(self):
        '''
        Return the set of hosts connected by add_host.
        '''
        return self._hosts

    @property
    @order_call_once(
        AS2CommonStates, AS2CommonStates.INITIALIZED)
    @order_call_once(
        AsyncDispatcherStates,
        AsyncDispatcherStates.INITIALIZED |
        AsyncDispatcherStates.RUNNING)
    def active_hosts(self):
        '''
        Return the number of active cluster nodes.
        '''
        return self.ev2citrusleaf_cluster_get_active_node_count(self._cluster)

    @order_call_once(
        AS2CommonStates, AS2CommonStates.INITIALIZED)
    @order_call_once(
        AsyncDispatcherStates,
        AsyncDispatcherStates.INITIALIZED |
        AsyncDispatcherStates.RUNNING)
    def add_host(self, host, port, timeout_ms=DEFAULT_TIMEOUT_MS):
        if not isinstance(host, bytes):
            host = host.encode('utf8')
        conn = (host, port,)
        if conn not in self._hosts:
            self._hosts.add(conn)
            code = self.ev2citrusleaf_cluster_add_host(
                self._cluster, host, port)
            if code:
                error_codes.aerospike_2_non_blocking_raise_error(code)

    @order_call_once(
        AS2CommonStates, AS2CommonStates.UNINITIALZED,
        AS2CommonStates.INITIALIZED)
    @order_call_once(
        AsyncDispatcherStates, AsyncDispatcherStates.INITIALIZED)
    def _create_cluster(self):
        self.ev2citrusleaf_init(self.ffi.NULL)
        self._cluster = self.ev2citrusleaf_cluster_create(
            self._event_loop, self._static_opts)
        self.ev2citrusleaf_cluster_set_runtime_options(
            self._cluster, self._options)

    @order_call_once(
        AS2CommonStates,
        AS2CommonStates.INITIALIZED,
        AS2CommonStates.UNINITIALZED)
    def _shutdown_cluster(self):
        self.ev2citrusleaf_cluster_destroy(self._cluster)
        self.ev2citrusleaf_shutdown(True)


@inherit_docstrings
class AS2Constructor(Constructor):
    def __init__(self, *args, **kwargs):
        '''
        Initialize the global data structures, create the event loop
        and start running it.
        '''
        self._setup_async()
        self._create_cluster()
        self._activate_loop()

    def shutdown(self):
        self._shutdown_cluster()
        try:
            self._deactivate_loop()
        except StateError:
            pass
        except Exception:
            raise
        self._destruct_async()


@inherit_docstrings
class AS2KeyOperations(KeyOperations):
    def __init__(self, *args, **kwargs):
        # prepare callback handlers
        self.bin_init_funcs = {
            int: self.ev2citrusleaf_object_init_int,
            bytes: self.ev2citrusleaf_object_dup_str,
            type(None): lambda obj, value: self.ev2citrusleaf_object_init(obj)
        }

    def select_key(self, callback, namespace, keyset, key_identifier,
                   timeout_ms=DEFAULT_TIMEOUT_MS, *named_bins_to_return):
        if not isinstance(namespace, six.binary_type):
            namespace = namespace.encode('utf8')
        if not isinstance(keyset, six.binary_type):
            keyset = keyset.encode('utf8')
        key_container, key_identifier = self._prepare_key(key_identifier)

        num_bins = len(named_bins_to_return)
        bins_ptr = self.ffi.new('char *', num_bins)
        bins_items = [self.ffi.new('char[]', bin_name)
                      for bin_name in named_bins_to_return]
        for index, named_bin_ptr in enumerate(bins_items):
            bins_ptr[index] = named_bin_ptr

        cuid = self._async_checkin(
            callback, [key_identifier,
                       key_container, namespace, keyset, bins_items, bins_ptr])
        self._submit_work(
            self.ev2citrusleaf_get,
            self._cluster, namespace, keyset, key_container,
            bins_ptr, num_bins, timeout_ms, self._handle_event_callback, cuid,
            self._event_loop)

    def get_key(self, callback, namespace, keyset,
                key_identifier, timeout_ms=DEFAULT_TIMEOUT_MS):
        '''
        Expects callback of form: f(error_code, bins, generation, expiration)
        '''
        if not isinstance(namespace, bytes):
            namespace = namespace.encode('utf8')
        if not isinstance(keyset, bytes):
            keyset = keyset.encode('utf8')
        # Get me an ev2citrusleaf_object pointer
        query_ptr, key_identifier = self._prepare_key(key_identifier)
        # Get me a uniq id and signal we want to hold
        # the query_ptr (avoid a GC)
        # Question:
        # 1. Since we strcopy the key_identifier into the
        #    ev2citrusleaf_object, can we let it be gc'ed?
        # 2. Are namespace and keyset needed to be preserved
        #    from a GC?
        cuid = self._async_checkin(
            callback, [query_ptr, namespace, keyset, key_identifier])
        # Send the work off to the event loop.
        self._submit_work(
            self.ev2citrusleaf_get_all,
            self._cluster, namespace, keyset, query_ptr,
            timeout_ms, self._handle_event_callback, cuid,
            self._event_loop)

    def put_key(self, callback, namespace, keyset,
                key_identifier, write_parameters=None,
                timeout_ms=DEFAULT_TIMEOUT_MS, **bin_names_to_values):
        if not isinstance(namespace, bytes):
            namespace = namespace.encode('utf8')
        if not isinstance(keyset, bytes):
            keyset = keyset.encode('utf8')
        if not bin_names_to_values:
            raise ValueError("No bins detected!")
        query_ptr, key_identifier = self._prepare_key(key_identifier)

        num_bins = len(bin_names_to_values.keys())
        bins = self.ffi.new('ev2citrusleaf_bin[]', num_bins)
        size_of_bin_name = self.ffi.sizeof(bins[0].bin_name) - 1
        for index, (key, value) in enumerate(bin_names_to_values.items()):
            length = len(key)
            if isinstance(value, six.string_types) and \
                    not isinstance(value, bytes):
                try:
                    value = value.encode('utf8')
                except UnicodeEncodeError:
                    raise UnicodeEncodeError(
                        ("Unable to convert value for bin "
                         "key {0} to bytes!").format(key))
            if isinstance(key, six.string_types) and \
                    not isinstance(key, bytes):
                try:
                    key = key.encode('utf8')
                except UnicodeEncodeError:
                    raise UnicodeEncodeError(
                        ("Unable to convert key for bin "
                         "key {0} to bytes!").format(key))

            if length > size_of_bin_name:
                raise ValueError(
                    "{0} too large a bin name to fit into {1} bytes!".format(
                        key, size_of_bin_name))
            bins[index].bin_name[0:length] = key
            try:
                self.bin_init_funcs[type(value)](
                    self.ffi.addressof(bins[index].object), value)
            except KeyError:
                raise ValueError(
                    "Unsupported type {0} for value of key {1}".format(
                        type(value), key))
        write_parameters_ptr = \
            self._checkout_write_parameters(write_parameters)
        cuid = self._async_checkin(
            callback,
            (key_identifier, query_ptr, namespace, keyset, bins,
             write_parameters_ptr, bin_names_to_values))
        self._submit_work(
            self.ev2citrusleaf_put,
            self._cluster, namespace, keyset, query_ptr,
            bins, num_bins, write_parameters_ptr,
            timeout_ms, self._handle_event_callback, cuid, self._event_loop)

    def remove_key(self, callback, namespace, keyset,
                   key_identifier, write_parameters=None,
                   timeout_ms=DEFAULT_TIMEOUT_MS):
        if not isinstance(namespace, bytes):
            namespace = namespace.encode('utf8')
        if not isinstance(keyset, bytes):
            keyset = keyset.encode('utf8')
        # Use the _prepare_key function to coerce key_identifier to
        # a container!
        key_ptr, key_identifier = \
            self._prepare_key(key_identifier)
        # Below:
        # This is an example of WHAT NOT to do:
        # key_ptr = self._checkout_ev2citrusleaf_obj()
        # self.ev2citrusleaf_object_dup_str(key_ptr, key_identifier)
        # Why not? Because it fails to recognize keys can be ints, etcs
        write_parameters_ptr = self._checkout_write_parameters(write_parameters)

        cuid = self._async_checkin(
            callback, (key_identifier, key_ptr,
                       write_parameters_ptr, namespace, keyset,))
        self._submit_work(
            self.ev2citrusleaf_delete,
            self._cluster, namespace, keyset, key_ptr,
            write_parameters_ptr, timeout_ms, self._handle_event_callback, cuid,
            self._event_loop)


@inherit_docstrings
class AS2Base(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self._ev2citrusleaf_obj_type = \
            self.ffi.typeof("ev2citrusleaf_object *")
        self._ev2write_parameters_type = \
            self.ffi.typeof('ev2citrusleaf_write_parameters *')
        self._ev2citrusleaf_digest_type = \
            self.ffi.typeof('cf_digest *')
        # map types to check in functions.
        self._common_checkin_funcs = {
            self._ev2citrusleaf_obj_type: self._checkin_ev2citrusleaf_obj,
            self._ev2write_parameters_type: self._checkin_write_parameters,
            self._ev2citrusleaf_digest_type: self._checkin_digest_container
        }
        self._handle_event_callback = \
            self.ffi.callback(EV2CALLBACK, self._handle_event_callback)
        self.NO_LOGGING = self._primary_library.CF_NO_LOGGING
        self.ERROR = self._primary_library.CF_ERROR
        self.WARN = self._primary_library.CF_WARN
        self.INFO = self._primary_library.CF_INFO
        self.DEBUG = self._primary_library.CF_DEBUG
        self._set_log_level(self.NO_LOGGING)

    def _get_log_level(self):
        return self._primary_library.g_log_level

    def _set_log_level(self, level):
        if not isinstance(level, six.integer_types):
            raise ValueError("Cannot coerce to a number.")
        self._primary_library.g_log_level = level

    def _handle_event_callback(
            self, return_value,  bins_ptr, n_bins,
            generation_val, expiration_val, udata_ptr):
        uid_cast = self.ffi.cast('char *', udata_ptr)
        id = self.ffi.string(uid_cast)
        callback, refs_to_hold = self._async_complete(id)
        for item in (x for x in refs_to_hold if isinstance(x, self.ffi.CData)):
            typeof = self.ffi.typeof(item)
            if typeof in self._common_checkin_funcs:
                self._common_checkin_funcs[typeof](item)

        bins = None
        try:
            code = None
            if return_value != error_codes.EV2CITRUSLEAF_OK:
                code = \
                    (return_value,
                     error_codes.aerospike_2_non_blocking_format_error(
                         return_value),)
            bins = {}
            for bin in (bins_ptr[index] for index in xrange(n_bins)):
                bins[filters.get_bin_name(bin, self.ffi)] = \
                    filters.get_value(
                        bin, bin.object.type, self.ffi)
                # You Do NOT need to free memory here, because
                # the finally clause does it for you.
                # Add in a manual dealloc and you will suffer double free
                # errors!
            return None
        except Exception:
            logger.exception(
                "Unexpected exception in _handle_event_callback! Fix it!")
        finally:
            callback(
                code, bins, generation_val, expiration_val)
            self.ev2citrusleaf_bins_free(bins_ptr, n_bins)

    def _prepare_key(self, keyname):
        '''
        Aerospike supports multiple types of keynames:
        - numerics (int, long)
        - byte strings
        - blobs (left alone) [Unimplemented!]

        Why are blobs Unimplemented? Because they can be:
            - Ruby blobs (How the hell do you read that into Python??!)
            - Java blobs (Only a small subset is supported by another package)
            - Python blobs (Should we REALLY support Python blobs but
                not the others?)
            - CSharp (see Java)
            - Generic blobs (WHY ARENT YOU USING A STRING?!?!)
        '''
        key_container = self._checkout_ev2citrusleaf_obj()
        ckey_name = None
        if isinstance(keyname, six.integer_types):
            # ckey_name = self.ffi.new('int64_t *', )
            self.ev2citrusleaf_object_init_int(key_container, keyname)
        # Python 2 strs succeed here
        # Python 3 bytes succeed here
        elif isinstance(keyname, six.binary_type):
            ckey_name = self.ffi.new('char []', keyname)
            self.ev2citrusleaf_object_init_str2(
                key_container, ckey_name, len(keyname))
        # Python 3 strs and Python 2 uncodes succeed here
        elif isinstance(keyname, six.string_types):
            keyname = keyname.encode('utf8')
            ckey_name = self.ffi.new('char []', keyname)
            self.ev2citrusleaf_object_init_str2(
                key_container, ckey_name, len(keyname))
        else:
            raise ValueError(
                ("Unsupported key type! "
                 "Must be a numeric, unicode string or bytes!"))
        return key_container, (keyname, ckey_name)

    def _generate_empty_citrusleaf_write_parameters(self):
        obj = self.ffi.new('ev2citrusleaf_write_parameters *')
        self._set_default_write_params(obj)
        return obj

    def _checkout_write_parameters(self, write_parameters=None):
        write_parameters_ptr = self.ffi.NULL
        if write_parameters is not None:
            write_parameters_ptr = self.generic_pool.checkout(
                self._ev2write_parameters_type,
                self._generate_empty_citrusleaf_write_parameters)
            for key, value in write_parameters.items():
                try:
                    setattr(write_parameters_ptr, key, value)
                except AttributeError:
                    raise ValueError(
                        ("write_parameters had incorrect key {0}. "
                         "Supported keys include: {1}").format(
                             key, ('use_generation', 'generation',
                                   'expiration', 'wpol',)))
                except TypeError:
                    raise TypeError(
                        "Incorrect value type {0} for key {1}".format(
                            type(value), key))
        return write_parameters_ptr

    def _set_default_write_params(self, write_parameters_ptr):
        write_parameters_ptr.use_generation = False
        write_parameters_ptr.generation = 0
        write_parameters_ptr.expiration = 0
        write_parameters_ptr.wpol = self._primary_library.CL_WRITE_ASYNC

    def _checkin_write_parameters(self, write_parameters_ptr):
        if self.ffi.typeof(write_parameters_ptr) is \
                self._ev2write_parameters_type:
            self.generic_pool.checkin(
                self._ev2write_parameters_type, write_parameters_ptr,
                self._set_default_write_params)

    def _checkout_ev2citrusleaf_obj(self):
        '''
        Use the built in object pool to keep track of
        malloced ev2citrusleaf_objects!
        '''
        return self.generic_pool.checkout(
            self._ev2citrusleaf_obj_type,
            self._generate_empty_citrusleaf_object)

    def _generate_empty_citrusleaf_object(self):
        return self.ffi.new("ev2citrusleaf_object *")

    def _checkin_ev2citrusleaf_obj(self, obj):
        assert self.ffi.typeof(obj) \
            is self._ev2citrusleaf_obj_type, \
            CHECKIN_OBJ_FAILURE.format('ev2citrusleaf_object *')
        self.generic_pool.checkin(
            self._ev2citrusleaf_obj_type,
            obj, self.ev2citrusleaf_object_set_null)

    def _generate_digest_container(self):
        return self.ffi.new('cf_digest *')

    def _checkin_digest_container(self, obj):
        assert self.ffi.typeof(obj) is \
            self._ev2citrusleaf_digest_type, \
            CHECKIN_OBJ_FAILURE.format('cf_digest*')
        self.generic_pool.checkin(
            self._ev2citrusleaf_digest_type, obj)

    def _checkout_digest_container(self):
        return self.generic_pool.checkout(
            self._ev2citrusleaf_digest_type, self._generate_digest_container)


@inherit_docstrings
class AS2Info(InfoOperations):
    def __init__(self, *args, **kwargs):
        self._info_cb = self.ffi.callback(
            ("void (*) (int return_value, char *response, "
             "size_t response_len, void *udata)"), self._info_cb)

    def _info_cb(self, return_value, response_bytes, length, user_data):
        uid_cast = self.ffi.cast('char *', user_data)
        id = self.ffi.string(uid_cast)
        callback, refs_to_hold = self._async_complete(id)
        try:
            callback(
                return_value,
                self.ffi.string(response_bytes, length))
        finally:
            self.free(response_bytes)

    def info(self, callback, hostname=None, timeout_ms=DEFAULT_TIMEOUT_MS):
        '''Return information on a single host or all of them'''
        if not hostname:
            try:
                hostname = tuple(self._hosts)[0]
            except IndexError:
                raise ValueError("No hosts connected.")
        cuid = self._async_checkin(
            callback, ())
        self._submit_work(
            self.ev2citrusleaf_info,
            self._event_loop, self._cluster.dns_base,
            hostname[0], hostname[1], self.ffi.NULL, timeout_ms,
            self._info_cb, cuid)


@inherit_docstrings
class AS2Digest(Digest):
    def __init__(self, *uint8_ts):
        assert len(self) == 20, "Invalid Digest!"

    def encode_container(self, container):
        for index, value in enumerate(self):
            container.digest[index] = value
        return container


@inherit_docstrings
class AS2DigestOperations(DigestOperations):
    def get_digest(self, callback, namespace, digest,
                   timeout_ms=DEFAULT_TIMEOUT_MS):
        '''Get bins for that digest.
        int ev2citrusleaf_get_all_digest(
            ev2citrusleaf_cluster *cl, char *ns, cf_digest *d, int timeout_ms,
            ev2citrusleaf_callback cb, void *udata, struct event_base *base)
        '''
        if not isinstance(namespace, six.binary_type):
            namespace = namespace.encode('utf8')
        digest_container = self._checkout_digest_container()
        digest.encode_container(digest_container)

        cuid = self._async_checkin(
            callback,
            [digest_container, namespace, digest])

        self._submit_work(
            self.ev2citrusleaf_get_all_digest,
            self._cluster, namespace, digest_container, timeout_ms,
            self._handle_event_callback, cuid, self._event_loop)

    def calculate_digest(self, keyset, keyname):
        '''Return the digest hash (bytes) for a key name.
        Useful for long keys, as we can send 20 bytes instead of a very
        long key name.
        '''
        if not isinstance(keyset, six.binary_type):
            keyset = keyset.encode('utf8')
        key_container, keyname = self._prepare_key(keyname)
        digest_container = self._checkout_digest_container()
        try:
            if (self.ev2citrusleaf_calculate_digest(
                    keyset, key_container, digest_container)) == -1:
                raise ValueError("Unknown data type for key!")
            return AS2Digest(digest_container.digest[i] for i in xrange(20))
        finally:
            self._checkin_digest_container(digest_container)
            self._checkin_ev2citrusleaf_obj(key_container)

    def remove_digest(self, callback, namespace, digest_identifier,
                      timeout_ms=DEFAULT_TIMEOUT_MS, write_parameters=None):
        '''
        Delete the digest hash.
        int ev2citrusleaf_delete_digest(
            ev2citrusleaf_cluster *cl, char *ns, cf_digest *d,
            ev2citrusleaf_write_parameters *wparam, int timeout_ms,
            ev2citrusleaf_callback cb, void *udata,
            struct event_base *base);
        '''
        if not isinstance(namespace, six.binary_type):
            namespace = namespace.encode('utf8')
        digest_container = digest_identifier.encode_container(
            self._checkout_digest_container())
        write_params = self._checkout_write_parameters(write_parameters)
        cuid = self._async_checkin(
            callback, [digest_container, namespace, write_params])
        self._submit_work(
            self.ev2citrusleaf_delete_digest,
            self._cluster, namespace, digest_container,
            write_params, timeout_ms, self._handle_event_callback, cuid,
            self._event_loop)


register(AS2DigestOperations, *VERSION)
register(AS2Info, *VERSION)
register(AS2Constructor, *VERSION)
register(LibEvent, *VERSION)
register(AS2CommonOperations, *VERSION)
register(AS2KeyOperations, *VERSION)
register(AS2Base, *VERSION)
