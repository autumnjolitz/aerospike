# -*- coding: utf-8 -*-
from .decorators import requires, warning
from .constants import DEFAULT_TIMEOUT_MS


class UnimplementedOperation(object):
    def __init__(self, *args, **kwargs):
        pass


class CommonOperations(UnimplementedOperation):
    @requires(2, 3)
    def add_host(self, host, port, timeout_ms=DEFAULT_TIMEOUT_MS):
        raise NotImplementedError

    @requires(2, 3)
    def _create_cluster(self):
        raise NotImplementedError

    @requires(2, 3)
    def _shutdown_cluster(self):
        raise NotImplementedError

    @property
    @requires(2, 3)
    def hosts(self):
        '''
        Return the set of hosts connected by add_host.
        '''
        raise NotImplementedError

    @property
    @requires(2, 3)
    def active_hosts(self):
        '''
        Return the number of active cluster nodes.
        '''
        raise NotImplementedError


class KeyOperations(UnimplementedOperation):
    @requires(2, 3)
    def get_key(
            self, callback, namespace, keyset,
            key_identifier, timeout_ms=DEFAULT_TIMEOUT_MS):
        '''
        Get all bins associated with this key.
        '''
        raise NotImplementedError

    @requires(2, 3)
    def put_key(self, callback, namespace, keyset,
                key_identifier, write_parameters=None,
                timeout_ms=DEFAULT_TIMEOUT_MS, **bin_names_to_values):
        '''Put the **bin_names_to_values (like bin1='abc')
        into the desired key_identifier.
        write_parameters are usually library specific, but are initialized
        to sensible defaults.

        To delete a bin, set it's value to None.
        '''
        raise NotImplementedError

    @requires(2, 3)
    def remove_key(self, callback, namespace, keyset, key_identifier):
        '''Delete the key'''
        raise NotImplementedError

    @requires(2, 3)
    def select_key(self, callback, namespace, keyset, key_identifier,
                   *named_bins_to_return):
        '''
        Aerospike 3 allows you to fetch specific bins from a record instead
        of all of them like get_key would.

        Aerospike 2 left buried in the SDK the same ability.
        '''
        raise NotImplementedError

    @requires(3)
    def exists_key(self, callback, namespace, keyset, key_identifier):
        '''Test if a key exists'''
        raise NotImplementedError

    @requires(3)
    def apply_user_function_key(self, callback, namespace, keyset,
                                key_identifier, func_name):
        '''Apply a user defined function (UDF) located by name to key'''
        raise NotImplementedError


class OperatorOperations(UnimplementedOperation):
    @requires(2)
    def key_pipeline(self, namespace, keyset, key_identifier,
                     create_key_if_missing=False):
        '''
        Aerospike allows you to do a set of operations on a given key.

        Used for safe read-modify-write.

        if create_key_if_missing is True, the missing key will be initialized
        with the first write operation.

        Returns an Aerospike KeyPipeline object that can be
        started with 'execute'
        '''
        raise NotImplementedError


class BatchOperations(UnimplementedOperation):
    @requires(2)
    def get_many_digests(self, callback, namespace, keyset, *digests):
        '''
        Fetch a list of digests (hashes for keys) in arospike.

        Grants many records
        '''
        raise NotImplementedError

    @requires(2, 3)
    def get_many_keys(self, callback, namespace, keyset, *key_identifiers):
        '''Like get_many_digests, except it operates on key names.'''
        raise NotImplementedError

    @requires(3)
    def exists_keys(self, callback, namespace, keyset, *key_identifiers):
        '''Test if many keys exist in the cluster'''
        raise NotImplementedError


class IndexOperations(UnimplementedOperation):
    @requires(3)
    def create_index(self, callback, namespace, keyset,
                     bin_name, index_name, index_type):
        '''
        Create an index on bin_name of type int or str with a specific name.
        '''
        raise NotImplementedError

    @requires(3)
    def remove_index(self, callback, namespace, index_name):
        '''Remove an index'''
        raise NotImplementedError


class InfoOperations(UnimplementedOperation):
    @requires(2, 3)
    def info(self, callback, hostname=None, timeout_ms=DEFAULT_TIMEOUT_MS):
        '''Return information on a single host or all of them'''
        raise NotImplementedError


class LargeDataOperations(UnimplementedOperation):
    '''
    I'm not implementing this yet.

    It's huge.
    '''


class QueryOperations(UnimplementedOperation):
    @requires(3)
    def query(self):
        '''Return a QueryBuilder object to operate on'''
        raise NotImplementedError


class ScanOperations(UnimplementedOperation):
    @warning(2, 'Scan runs as a background operation on AS2 '
             'and will be of poor performance')
    @requires(2, 3)
    def scan(self):
        '''Return a ScanBuilder to operate on'''
        raise NotImplementedError


class DigestOperations(UnimplementedOperation):
    '''
    Digests are hash identifiers formed from keyset and
    keynames inside a cluster.
    '''
    @requires(2)
    def get_digest(self, callback, namespace, digest_identifier,
                   timeout_ms=None):
        '''Get bins for that digest.'''
        raise NotImplementedError

    @requires(2)
    def calculate_digest(self, keyset, keyname):
        '''Return the digest hash for a key name. Useful for long keys, as
        we can send 20 bytes instead of a very long key name.
        '''
        raise NotImplementedError

    @requires(2)
    def remove_digest(self, callback, namespace, digest_identifier,
                      timeout_ms=DEFAULT_TIMEOUT_MS, write_parameters=None):
        '''
        Delete the digest hash.
        '''
        raise NotImplementedError


class UserDefinedFunctionsOperations(UnimplementedOperation):
    @requires(3)
    def get_udf(self, callback, udf_name, udf_type):
        '''
        Return a UserDefinedFunctionFile instance
        '''
        raise NotImplementedError

    @requires(3)
    def list_udfs(self, callback):
        '''
        Return a list of tuples of form (udf_name, udf_type, udf_hash)
        '''
        raise NotImplementedError

    @requires(3)
    def upload_udf(self, callback, udf_name, udf_type, udf_content):
        '''Upload a user defined function to Aerospike'''
        raise NotImplementedError

    @requires(3)
    def remove_udf(self, callback, udf_name):
        '''Delete a udf from the cluster'''
        raise NotImplementedError
