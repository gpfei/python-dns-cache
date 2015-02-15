import asyncio
import logging

from dnslib import DNSRecord

from dns_cache.cache import Cache


logger = logging.getLogger(__name__)


class UDPClientProtocol(asyncio.DatagramProtocol):
    """
    Used to connect remote DNS server, like 8.8.8.8

    """

    def __init__(self, query_q, result_q):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q
        self.client_dict = {}

        asyncio.async(self.send_query())

    def connection_made(self, transport):
        logger.info("Connection made.")
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.debug("<<<< {} from {}".format(data, addr))

        dns = DNSRecord.parse(data)
        key = (dns.header.id, dns.q.qname, dns.q.qtype)
        addr = self.client_dict[key]

        asyncio.async(self.result_q.put((data, addr)))

    def error_received(self, exc):
        logger.error('Error received:', exc)

    def connection_lost(self, exc):
        logger.info("Socket closed, stop the event loop")
        loop = asyncio.get_event_loop()
        loop.stop()

    @asyncio.coroutine
    def send_query(self):
        while True:
            data, addr = yield from self.query_q.get()
            dns = DNSRecord.parse(data)
            key = (dns.header.id, dns.q.qname, dns.q.qtype)
            self.client_dict[key] = addr
            logger.debug('>>>> {}'.format(data))
            self.transport.sendto(data)


class TCPClientProtocol(asyncio.Protocol):
    """
    Used to connect remote DNS server, like 8.8.8.8

    """

    def __init__(self, query_q, result_q):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q

        asyncio.async(self.send_query())

    def connection_made(self, transport):
        logger.info("Connection made.")
        self.transport = transport

    def data_received(self, data):
        logger.debug("<<<< {} from {}".format(data, self.transport))

        dns = DNSRecord.parse(data)
        key = (dns.header.id, dns.q.qname, dns.q.qtype)

        asyncio.async(self.result_q.put((data, key)))

    def error_received(self, exc):
        logger.error('Error received:', exc)

    def connection_lost(self, exc):
        logger.info("Socket closed, stop the event loop")
        loop = asyncio.get_event_loop()
        loop.stop()

    @asyncio.coroutine
    def send_query(self):
        while True:
            data, key = yield from self.query_q.get()
            logger.debug('>>>> {}'.format(key))
            self.transport.write(data)


class BaseClient():

    def __init__(self, host, port, query_q, result_q):
        self.host = host
        self.port = port
        self.query_q = query_q
        self.result_q = result_q

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.connect())

    @asyncio.coroutine
    def connect(self):
        pass


class UDPClient(BaseClient):

    @asyncio.coroutine
    def connect(self):
        logger.debug('UDPClient connect.')
        self.transport, self.protocol = yield from self.loop.create_datagram_endpoint(
            lambda: UDPClientProtocol(self.query_q, self.result_q),
            remote_addr=(self.host, self.port))


class TCPClient(BaseClient):

    @asyncio.coroutine
    def connect(self):
        logger.debug('TCPClient connect.')
        self.client = yield from self.loop.create_connection(
            lambda: TCPClientProtocol(self.query_q, self.result_q),
            self.host, self.port)
