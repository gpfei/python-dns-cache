import asyncio
import logging

from dnslib import DNSRecord


logger = logging.getLogger(__name__)


class ClientProtocol(asyncio.DatagramProtocol):
    """
    Used to connect remote DNS server, like 8.8.8.8

    """

    def __init__(self, query_q, result_q):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q
        self.query_dict = {}
        asyncio.async(self.send_query())

    def connection_made(self, transport):
        logger.info("Connection made.")
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.debug("<<<< {} from {}".format(data, addr))

        dns = DNSRecord.parse(data)
        key = (dns.header.id, dns.q.qname, dns.q.qtype)
        addr = self.query_dict[key]

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
            self.query_dict[key] = addr
            logger.debug('>>>> {}'.format(data))
            self.transport.sendto(data)
