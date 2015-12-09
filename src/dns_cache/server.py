import asyncio
import logging
import random

from client import TCPClientProtocol
from dnslib import DNSRecord, DNSError
from settings import REMOTE_SERVERS

logger = logging.getLogger(__name__)



class DirectUDPClientProtocol(asyncio.DatagramProtocol):
    """
    Used for invalid DNS query

    """
    def __init__(self, data, client_addr):
        super().__init__()
        self.data = data
        self.client_addr = client_addr

        loop = asyncio.get_event_loop()
        loop.call_later(5, self.close)

    def close(self):
        logger.debug('direct udp client closing...')
        if hasattr(self, 'transport'):
            self.transport.close()

    def connection_made(self, transport):
        self.transport = transport
        self.transport.sendto(self.data)

    def datagram_received(self, data, addr):
        logger.debug("<<<< {} from {}".format(data, addr))
        self.transport.sendto(data, self.client_addr)
        self.transport.close()

    def error_received(self, exc):
        logger.error('Error received:', exc)


class UDPServerProtocol(asyncio.DatagramProtocol):

    """
    Used to provide dns cache service.

    """

    def __init__(self, query_q, result_q, client_dict):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q
        self.client_dict = client_dict

    def connection_made(self, transport):
        logger.info("Local UDP Connection made.")
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.debug('<<<< {} from {}'.format(data, addr))

        try:
            dns = DNSRecord.parse(data)
            key = (dns.header.id, dns.q.qname, dns.q.qtype)
            self.client_dict[key] = addr
        except DNSError:
            logger.info('Invalid DNS query from {}. {}'.format(addr, data))
            asyncio.async(self.query_directly(data, addr))
        else:
            asyncio.async(self.query_q.put((data, key)))

    @asyncio.coroutine
    def query_directly(self, data, addr):
        host, port = random.choice(REMOTE_SERVERS)
        logger.warn('{}, {}'.format(host, port))
        loop = asyncio.get_event_loop()
        transport, protocol = yield from loop.create_datagram_endpoint(
            lambda: DirectUDPClientProtocol(data, addr),
            remote_addr=(host, port))


class TCPServerProtocol(asyncio.Protocol):

    """
    Used to provide dns cache service.

    """

    def connection_made(self, transport):
        logger.debug('Local connection made.')
        self.transport = transport

        try:
            peername = transport.get_extra_info('peername')
            logger.debug('Local Connection from {}'.format(peername))
        except Exception:
            logger.exception('---')

        self.server_conn = loop.create_task(self.connect_remote_server())

    @asyncio.coroutine
    def connect_remote_server(self):
        logger.debug('TCPClient connect remote server.')
        server_conn = yield from self.loop.create_connection(
            lambda: TCPClientProtocol(self),
            host, port)
        logger.debug('TCPClient connect remote server done.')
        return server_conn

    def data_received(self, data):
        logger.debug('<<<< {} from {}'.format(data, self.transport))
        self.server_conn.send_data(data)

    def send_data(self, data):
        self.transport.write(data)


class UDPServer():

    def __init__(self, host, port, query_q=None, result_q=None):
        self.host = host
        self.port = port
        self.query_q = query_q
        self.result_q = result_q
        self.client_dict = {}
        self.transport = None

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.listen())
        self.loop.create_task(self.send_result())

    @asyncio.coroutine
    def listen(self):
        logger.debug('UDPServer listen.')
        self.transport, self.protocol = yield from self.loop.create_datagram_endpoint(
            lambda: UDPServerProtocol(self.query_q, self.result_q, self.client_dict),
            local_addr=(self.host, self.port))

    @asyncio.coroutine
    def send_result(self):
        while True:
            data, key = yield from self.result_q.get()
            addr = self.client_dict.get(key)
            if addr:
                logger.debug('>>>> {} to {}'.format(data, addr))
                self.transport.sendto(data, addr)
            else:
                yield from self.result_q.put((data, key))


class TCPServer():

    def __init__(self, host, port, servers):
        self.host = host
        self.port = port

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.listen())
        self.loop.create_task(self.send_result())

    @asyncio.coroutine
    def listen(self):
        logger.debug('TCPServer listen.')
        self.server = yield from self.loop.create_server(
            TCPServerProtocol,
            self.host, self.port)
        logger.debug('TCPServer listen done.')


@asyncio.coroutine
def handle_tcp(reader, writer):
    """
    Using high-level API for Streams

    """
    loop = asyncio.get_event_loop()

    try:
        r_host, r_port = random.choice(REMOTE_SERVERS)
        r_reader, r_writer = \
            yield from asyncio.open_connection(r_host, r_port, loop=loop)

        data = yield from reader.read(4096)
        logger.debug('<<<< TCP Recv from client: {}'.format(data))

        r_writer.write(data)
        yield from r_writer.drain()

        r_data = yield from r_reader.read(4096)
        logger.debug('<<<< TCP Recv from remote server: {}'.format(r_data))

        writer.write(r_data)
        yield from writer.drain()
    finally:
        r_writer.close()
        writer.close()
