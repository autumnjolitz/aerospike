import functools
import optparse
import threading
import time
try:
    import readline
except ImportError:
    pass
else:
    import rlcompleter
    readline.parse_and_bind("tab: complete")
import code
import six
import inspect
import textwrap

ASYNC_SYNC_FORMAT = \
    """{async_form}
(blocking) {sync_name}{sync_args}"""

BANNER = """Aerospike CLI tool

This primitive tool wraps an Aerospike Client instance!

All asynchronous commands that take a callback as the first
argument have a synchronous (blocking) version -- simple prepend
'bl_' to the function name.

Example:
    >>> bl_info()
    ...

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
"""

CLI_DESCRIPTION = """Command line interface using the Python
aerospike driver.
"""
CLI_USAGE = "usage: %prog --host HOST [--port PORT]"


class WrapperDict(dict):
    def __init__(self, obj, lookaside):
        self.obj = obj
        self.arg_wrapper = \
            textwrap.TextWrapper(subsequent_indent='      ', width=79)
        self.wrapper = \
            textwrap.TextWrapper(
                initial_indent='   ', subsequent_indent='   ', width=79)
        self.lookaside = lookaside

    def __getitem__(self, key):
        if key.lower() == 'commands':
            print(self.commands())
        elif key.lower() == 'intro':
            print(BANNER)
        else:
            try:
                # if key.endswith('_b') and hasattr(self.obj, key[:-2]):
                #     obj = getattr(self.obj, key[:-2])
                #     if not six.callable(obj):
                #         raise AttributeError
                #     return turn_async_into_sync(obj)
                # else:
                obj = getattr(self.obj, key)
                if key in self.lookaside:
                    raise AttributeError
                return obj
            except AttributeError:
                try:
                    return self.lookaside[key]
                except KeyError:
                    return dict.__getitem__(self, key)
                raise KeyError

    def keys(self):
        return dir(self.obj)

    def __iter__(self):
        for i in dir(self.obj):
            yield i, self[i]
        # yield 'commands', self.commands

    def commands(self, all=False):
        '''
        List the functions/properties available on the Aerospike Client.
        '''
        #
        # Developer's note:
        # This is quite complex. First, we override and decorate functions,
        # losing the original argument specification, so we must be able to
        # extract the original function is a must.
        # Ignoring non-callable/c funcs/non-property items is a pain in the ass
        #
        # Finally, we can't get the original documentation due to Python
        # losing the mixin origin.
        #
        buf = ['Commands Available:']
        for obj_name in dir(self.obj):
            # Should we list every callable and property?
            if not all:  # nope.
                # Is it is private/pseudo-private method?
                if obj_name.startswith('_'):
                    continue
                # Is it a wrapped c-function?
                if obj_name in self.obj._wrapped_cfuncs:
                    continue
            actual_obj = getattr(self.obj, obj_name)
            docstrings = None
            args = None
            potential_argument_specification = None
            if hasattr(type(self.obj), obj_name) and \
                    isinstance(getattr(type(self.obj), obj_name), property):
                potential_argument_specification = ['']
                docstrings = \
                    getattr(type(self.obj), obj_name).__doc__ or \
                    'Set/Get this property'
            elif six.callable(actual_obj):
                # get the Argument spec
                # Example:
                # def f(a, b, c=5)
                # Will return:
                # (a, b, c=5)
                # from the function.
                args = inspect.getargspec(actual_obj)
                current_obj = actual_obj
                # If it is decorated, try to reach the original function.
                while hasattr(current_obj, 'orig_func'):
                    current_obj = current_obj.orig_func
                    args = inspect.getargspec(current_obj)
                if args.args and args.args[0] == 'self':
                    args.args.pop(0)
                potential_argument_specification = inspect.formatargspec(*args)
                # Break the blob of arguments into an array of strings:
                # IE:
                # SOMEGIANTBLOBOFTEXTBLAHBLAHBLAH
                # ->
                # ['SOMEGIANT', '   BLOBOFTEXT', '  BLAHBLAHBLAH']
                # This means we can have the documentation on the same
                # line as the function name and beginning arguments
                # while wrapping the rest to the next few lines neatly.
                potential_argument_specification = \
                    self.arg_wrapper.wrap(potential_argument_specification)
            else:
                continue
            # Let's get the documentation!
            if hasattr(actual_obj, '__doc__'):
                if not docstrings:
                    docstrings = \
                        actual_obj.__doc__ or 'No documentation found'
            if docstrings.count('\n') > 1:
                docstrings = docstrings.split('\n')
                docstrings = docstrings[0] + \
                    textwrap.dedent('\n'.join(docstrings[1:]))
            docstrings = self.wrapper.wrap(docstrings)
            obj_pair = "{func_name}{args}".format(
                func_name=obj_name,
                args='\n'.join(potential_argument_specification))
            if args and args.args and args.args[0] == 'callback':
                args.args.pop(0)
                obj_pair = \
                    ASYNC_SYNC_FORMAT.format(
                    async_form=obj_pair, sync_name=obj_name+'_b',
                    sync_args='\n'.join(self.arg_wrapper.wrap(
                        inspect.formatargspec(*args))))
            buf.append(
                '{obj_pair}\nType: {type}\n{description}\n'.format(
                    obj_pair=obj_pair,
                    type=type(actual_obj).__name__,
                    description='\n'.join(docstrings)))
        return '\n'.join(buf)


def gather_cli_options():
    parser = optparse.OptionParser(description=CLI_DESCRIPTION, usage=CLI_USAGE)
    parser.add_option(
        '--host', help="host to connect to", type='str')
    parser.add_option(
        '--port', help="port to connect on (defaults to 3000)", type="int",
        default=3000)
    options, _ = parser.parse_args()
    options = dict(options.__dict__)
    if not (options.get('host') and options.get('port')):
        print("Missing host/port")
        parser.print_help()
        raise SystemExit()
    return options


def interpreter(aerospike_client):
    lookaside = {}
    lookaside.update(locals())
    lookaside.update(globals())
    lookaside['client'] = aerospike_client
    try:
        lookaside.update(__builtins__)
    except TypeError:
        lookaside.update(vars(__builtins__))

    shell = code.InteractiveConsole(
        WrapperDict(aerospike_client, lookaside=lookaside))
    shell.interact(banner=BANNER)
