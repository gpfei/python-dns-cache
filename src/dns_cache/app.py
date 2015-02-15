import asyncio
import logging

from dns_cache.client import TCPClient, UDPClient
from dns_cache.server import TCPServer, UDPServer


logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


def main():
    query_q = asyncio.Queue()
    result_q = asyncio.Queue()

    loop = asyncio.get_event_loop()

    logger.debug('Creating UDP server ...')
    udp_server = UDPServer('127.0.0.1', 53, query_q, result_q)

    #logger.debug('Creating TCP server ...')
    #tcp_server = TCPServer('127.0.0.1', 53, query_q, result_q)

    logger.debug('Connecting ...')
    #tcp_client = TCPClient('223.5.5.5', 53, query_q, result_q)
    udp_client = UDPClient('223.5.5.5', 53, query_q, result_q)

    logger.debug('Running ...')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    #s_transport.close()
    #server.close()
    #c_transport.close()
    loop.close()


if __name__ == '__main__':
    main()
