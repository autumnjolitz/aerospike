'Test the driver on a local aerospike server (usually via vagrant)'
import unittest
import aerospike
from unittest.mock import Mock
import string
import random
from six.moves import range as xrange
from threading import Lock
import functools
import time
import six


def get_random_key(length):
    return ''.join(
        random.choice(
            string.ascii_letters) for x in xrange(length))


def random_value():
    return random.choice(
        [get_random_key,
         functools.partial(random.randint, 1)])(random.randint(1, 40))


def fold_to_bytes(source):
    result = {}
    for key, value in source.items():
        if isinstance(
                key, six.string_types + (six.binary_type,)) \
                and not isinstance(key, type(b'')):
            key = key.encode('utf8')
        if isinstance(value, six.string_types + (six.binary_type,)) \
                and not isinstance(value, type(b'')):
            value = value.encode('utf8')
        result[key] = value
    return result


def callback(mock_obj, counter, lock):
    def real_callback(*args):
        mock_obj(*args)
        with lock:
            counter['value'] -= 1
    return real_callback

NUM_TESTS = 100


class TestStability(unittest.TestCase):
    def setUp(self):
        self.client = aerospike.get_client()
        self.client.add_host('127.0.0.1', 3000)
        self.namespace = 'test'
        self.keyset = 'Aerospike'
        self.lock = Lock()
        self.counter = {'value': 0}
        self.mocks = \
            dict((get_random_key(31),
                 (Mock(), dict((get_random_key(10), random_value()) for i in
                  xrange(random.randint(1, 10))))) for _ in range(NUM_TESTS))
        self.test_vector = [
            (id,
             callback(mock, self.counter, self.lock),
             value) for id, (mock, value) in self.mocks.items()]

    def test_put_and_get_and_remove(self):
        self.counter['value'] = len(self.test_vector)
        t_s = time.time()
        for identifier, callback, values in self.test_vector:
            self.client.put_key(
                callback, self.namespace, self.keyset, identifier,
                timeout_ms=1000, **values)
        while self.counter['value'] > 0:
            time.sleep(0.01)
        else:
            t_e = time.time()
            print('{0} puts took {1:.2f} seconds'.format(
                len(self.test_vector), t_e - t_s))
        successes = timeouts = 0
        for identifier, (mock, _) in self.mocks.items():
            try:
                mock.assert_called_with(None, {}, 1, 0)
                successes += 1
            except AssertionError:
                if mock.call_args[0][0][0] != -2:
                    raise
                timeouts += 1
        print("Breakdown\nSuccessful key puts: {0}\nTimeouts: {1}".format(
            successes, timeouts))

        self.counter['value'] = len(self.test_vector)
        t_s = time.time()
        for identifier, callback, values in self.test_vector:
            self.client.get_key(
                callback, self.namespace, self.keyset, identifier,
                timeout_ms=1000)
        while self.counter['value'] > 0:
            time.sleep(0.01)
        else:
            t_e = time.time()
            print('{0} gets took {1:.2f} seconds'.format(
                len(self.test_vector), t_e - t_s))
        successes = missing = timeouts = 0
        for identifier, (mock, values) in self.mocks.items():
            try:
                mock.assert_called_with(None, fold_to_bytes(values), 1, 0)
                successes += 1
            except AssertionError:
                if mock.call_args[0][0][0] == 2:
                    missing += 1
                    continue
                if mock.call_args[0][0][0] != -2:
                    raise
                timeouts += 1
        print("Breakdown\n\
Successful key gets: {0}\n\
Timeouts: {1}\nMissing keys: {2}".format(
            successes, timeouts, missing))

        # for identifier, callback, values in self.test_vector:
        #     self.client.remove(
        #         callback, self.namespace, self.keyset, identifier,
        #         timeout_ms=1000)



if __name__ == '__main__':
    unittest.main()
