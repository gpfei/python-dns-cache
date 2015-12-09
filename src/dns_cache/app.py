import asyncio
import logging
import traceback

from client import UDPClient
from server import UDPServer, handle_tcp
from settings import REMOTE_SERVERS, LISTEN


logging.basicConfig(level=logging.WARN)

logger = logging.getLogger(__name__)


def main():
    loop = asyncio.get_event_loop()

    UDP = True
    TCP = False

    udp_server = tcp_server = None

    host, port = LISTEN

    if UDP:
        query_q = asyncio.Queue()
        result_q = asyncio.Queue()

        logger.debug('Creating UDP server ...')
        udp_server = UDPServer(host, port, query_q, result_q)

        logger.debug('Connecting ...')
        udp_client = UDPClient(REMOTE_SERVERS, query_q, result_q)

    if TCP:
        logger.debug('Creating TCP server ...')
        coro = asyncio.start_server(handle_tcp, host, port, loop=loop)
        tcp_server = loop.run_until_complete(coro)

    logger.debug('Running ...')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()

    if tcp_server:
        tcp_server.close()
        loop.run_until_complete(tcp_server.wait_closed())

    #s_transport.close()
    #server.close()
    #c_transport.close()
    loop.close()


if __name__ == '__main__':
    main()
