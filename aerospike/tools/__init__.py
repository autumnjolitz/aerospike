
from . import cli
cli
from .cli import gather_cli_options, interpreter
import aerospike
from aerospike.common import StateError


def setup_cli():
    """Entry point for the application script"""
    options = gather_cli_options()
    client = aerospike.get_client()
    print("Connecting to {0}:{1} for initial cluster discovery...".format(
        options['host'], options['port']))
    client.add_host(options['host'], options['port'])
    interpreter(client)

    try:
        client.shutdown()
    except StateError:
        pass
