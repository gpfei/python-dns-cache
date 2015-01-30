import asyncio
import logging

from dns_cache.server import ServerProtocol
from dns_cache.client import ClientProtocol


logging.basicConfig(level=logging.DEBUG)


def main():
    query_q = asyncio.Queue()
    result_q = asyncio.Queue()
    loop = asyncio.get_event_loop()

    listen = loop.create_datagram_endpoint(
        lambda: ServerProtocol(query_q, result_q),
        local_addr=('127.0.0.1', 53))
    s_transport, s_protocol = loop.run_until_complete(listen)

    connect = loop.create_datagram_endpoint(
        lambda: ClientProtocol(query_q, result_q),
        remote_addr=('223.5.5.5', 53))
    c_transport, c_protocol = loop.run_until_complete(connect)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    s_transport.close()
    c_transport.close()
    loop.close()

if __name__ == '__main__':
    main()
