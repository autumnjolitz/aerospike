Python Non-blocking interface to Aerospike C libraries
================

A CFFI-based driver for the Aerospike 2/3 C clients suitable for CPython and PyPy 2.6/2.7/3.3 interpreters.

It can detect and load compatible Aerospike C client libraries automatically.

Includes a tool named ```aerospike-cli```, inspired by ```redis-cli```, that can provide a REPL-like interface to an Aerospike cluster.


Status
-----

Aerospike 2 LibEvent:

* Operations Supported:
    * Key Operations
    * Info Operations
    * Digest Operations

Aerospike 2/3 blocking libraries:

* Blockers
    * something that simulates non-blocking, probably by using threads and a lock free queue.
* Operations Supported:
    * None


Usage
-----

```
>>> import aerospike
>>> client = aerospike.get_client()
>>> client.add_host('XXX.XXX.XXX.XXXX', 3000)
>>> def get_cb(errors, bins, generation, expiration):
...     print(errors, bins)
... 
>>> client.get_key(
...     get_key_callback,
...     namespace, keyset,
...     keyname, 1000)
>>>
```


aerospike-cli
-------------

```
$ aerospike-cli --host 127.0.0.1 --port 4004
Connecting to 127.0.0.1:4004 for initial cluster discovery...
Aerospike CLI tool

This primitive tool wraps an Aerospike Client instance!

To list commands available:
    >>> commands
    Commands Available:
    ...
    >>>

To get help on a command (like add_host):
    >>> help(add_host)

To access the client object, simply refer to 'client':
   >>> client
   <abc.Aerospike2Nonblocking object at 0x107f9b9d0>

To show all memebers on the client object:
   >>> dir()
   ...
   >>> dir(client)
   ...

To show this message again, type intro

>>> active_hosts
1
>>> hosts
{(b'127.0.0.1', 4004)}
>>> 
```

