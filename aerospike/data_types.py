import abc


class Digest(tuple):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def encode_container(digest_container):
        '''
        Digests are arrays of integers denoting a uniq id.

        This function must be able to encode a C-level digest
        container object from the array encoded within.
        '''
        raise NotImplementedError
