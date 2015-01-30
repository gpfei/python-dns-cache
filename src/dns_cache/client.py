import asyncio

from dnslib import DNSRecord


class ClientProtocol(asyncio.DatagramProtocol):
    """
    Used to connect remote DNS server, like 8.8.8.8

    """

    def __init__(self, query_q, result_q):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q
        self.query_dict = {}
        self.sending_query = False

    def connection_made(self, transport):
        self.transport = transport

    @asyncio.coroutine
    def _datagram_received(self, data, addr):
        if not self.sending_query:
            asyncio.async(self.send_query)
            self.sending_query = True

        print('client ...', data, addr)
        yield from self.result_q.put((data, addr))

    def datagram_received(self, data, addr):
        print("Client Received:", data)
        dns = DNSRecord.parse(data)
        key = (dns.header.id, dns.q.qname, dns.q.qtype)
        addr = self.query_dict(key)

        self._datagram_received(data, addr)

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Socket closed, stop the event loop")
        loop = asyncio.get_event_loop()
        loop.stop()

    @asyncio.coroutine
    def send_query(self):
        data, addr = yield from self.query_q.get()
        dns = DNSRecord.parse(data)
        key = (dns.header.id, dns.q.qname, dns.q.qtype)
        self.query_dict[key] = addr
        seld.transport.sendto(data)
