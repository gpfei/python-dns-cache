import asyncio
import logging

from dnslib import DNSRecord, DNSError


logger = logging.getLogger(__name__)


class UDPClientProtocol(asyncio.DatagramProtocol):
    """
    Used to connect remote DNS server, like 8.8.8.8

    """

    def __init__(self, client, query_q, result_q):
        super().__init__()
        self.client = client
        self.query_q = query_q
        self.result_q = result_q
        self.client_dict = {}

        asyncio.async(self.send_query())

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        logger.info('Connection to {}'.format(peername))
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.debug("<<<< {} from {}".format(data, addr))

        try:
            dns = DNSRecord.parse(data)
            key = (dns.header.id, dns.q.qname, dns.q.qtype)
            addr = self.client_dict.pop(key)
        except (DNSError, KeyError):
            logger.info('Invalid DNS answer from {}. {}'.format(addr, data))
        else:
            asyncio.async(self.result_q.put((data, addr)))

    def error_received(self, exc):
        logger.error('Error received:', exc)

    def connection_lost(self, exc):
        logger.debug('The remote UDP server closed the connection. '
                     'Re-connecting ...')
        loop = asyncio.get_event_loop()
        loop.create_task(self.client.connect())

    @asyncio.coroutine
    def send_query(self):
        if getattr(self, '__sending_query', None):
            return
        else:
            setattr(self, '__sending_query', True)

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

    def __init__(self, client):
        super().__init__()
        self.client = client

    def connection_made(self, transport):
        logger.info("Remote TCP Connection made.")
        self.transport = transport

    def data_received(self, data):
        logger.debug("<<<< {} from {}".format(data, self.transport))
        self.client.send_data(data)

    def send_data(self, data):
        self.transport.write(data)

    def error_received(self, exc):
        logger.error('Error received:', exc)

    def connection_lost(self, exc):
        logger.debug('The remote TCP server closed the connection. '
                     'Re-connecting ...')


class UDPClient():

    def __init__(self, servers, query_q, result_q):
        self.servers = servers
        self.query_q = query_q
        self.result_q = result_q

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.connect())

    @asyncio.coroutine
    def connect(self):
        logger.debug('UDPClient connecting remote servers.')

        for host, port in self.servers:
            transport, protocol = yield from self.loop.create_datagram_endpoint(
                lambda: UDPClientProtocol(self, self.query_q, self.result_q),
                remote_addr=(host, port))

        logger.debug('UDPClient connect done.')
