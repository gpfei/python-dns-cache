import asyncio


class ServerProtocol(asyncio.DatagramProtocol):

    """
    Used to provide dns cache service.

    """

    def __init__(self, query_q, result_q):
        super().__init__()
        self.query_q = query_q
        self.result_q = result_q
        self.sending_result = False
        self.loop = asyncio.get_event_loop()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(addr)
        print('Received %r from %s' % (data, addr))

        if not self.sending_result:
            asyncio.async(self.send_result)
            self.sending_result = True

        self.loop.run_until_complete(self.query_q.put((data, addr)))
        print(self.query_q)

    @asyncio.coroutine
    def send_result(self):
        data, addr = yield from self.result_q.get()
        print('Send %r to %s' % (data, addr))
        self.transport.sendto(data, addr)
