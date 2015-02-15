import asyncio
import logging


logger = logging.getLogger(__name__)


class UDPServerProtocol(asyncio.DatagramProtocol):

    """
    Used to provide dns cache service.

    """

    def __init__(self, query_q, result_q, client_dict):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q
        self.client_dict = client_dict

        asyncio.async(self.send_result())

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.debug('<<<< {} from {}'.format(data, addr))

        dns = DNSRecord.parse(data)
        key = (dns.header.id, dns.q.qname, dns.q.qtype)
        self.client_dict[key] = addr

        asyncio.async(self.query_q.put((data, key)))


class TCPServerProtocol(asyncio.Protocol):

    """
    Used to provide dns cache service.

    """

    def __init__(self, query_q, result_q):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        logger.debug('<<<< {} from {}'.format(data, self.transport))
        asyncio.async(self.query_q.put((data, self.transport)))


class BaseServer():

    def __init__(self, host, port, query_q, result_q):
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
        pass

    @asyncio.coroutine
    def send_result(self):
        pass


class UDPServer(BaseServer):

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


class TCPServer(BaseServer):

    @asyncio.coroutine
    def listen(self):
        logger.debug('TCPServer listen.')
        self.server = yield from self.loop.create_server(
            lambda: TCPServerProtocol(self.query_q, self.result_q, self.client_dict),
            self.host, self.port)

    @asyncio.coroutine
    def send_result(self):
        while True:
            data, key = yield from self.result_q.get()
            addr = self.client_dict(key)
            if isinstance(addr, tuple):
                # let udp server send
                yield from self.result_q.put((data, transport))
            else:
                logger.debug('>>>> TCP {} to {}'.format(data, addr))
                transport.write(data)
