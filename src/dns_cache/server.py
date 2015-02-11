import asyncio
import logging


logger = logging.getLogger(__name__)


class ServerProtocol(asyncio.DatagramProtocol):

    """
    Used to provide dns cache service.

    """

    def __init__(self, query_q, result_q):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q

        asyncio.async(self.send_result())

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.debug('<<<< {} from {}'.format(data, addr))
        asyncio.async(self.query_q.put((data, addr)))

    @asyncio.coroutine
    def send_result(self):
        while True:
            data, addr = yield from self.result_q.get()
            logger.debug('>>>> {} to {}'.format(data, addr))
            self.transport.sendto(data, addr)
