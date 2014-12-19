Aerospike Driver
=======================

This provides a CFFI based driver to an Aerospike server. Can be used with Aerospike 2 or Aerospike 3 C libraries.

You must install one of the Aerospike C clients to make use of this driver.

Provides:
    - Asynchronous callback capabilities
    - AsyncIO support (planned)
    - Tornado wrappers (planned)


Current things that do not work:
   - setting bins with int values is FUBAR

For Aerospike 2 C client, there are two possibilies:
    - LibEvent-based (non-blocking)
    - Synchronous (blocking)

The Aerospike 3 C client is synchronous only.

Blocking C clients will make use of a thread pool to simulate asynchronous operations. Non-blocking C clients will make use of an LibEvent event loop.

Also provides a command line interface (aerospike-cli) that wraps an Aerospike Client instance and provides a Pythonic interpreter to operate with.
