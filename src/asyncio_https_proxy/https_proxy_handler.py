import asyncio


class HTTPSProxyHandler:
    """
    An instance of a connection from a client to the HTTPS proxy server

    Each new client connection will create a new instance of this class.
    """

    client_reader: asyncio.StreamReader
    client_writer: asyncio.StreamWriter

    async def client_connected(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        """
        A client has connected to the proxy and sent a valid request.

        Override this method to implement custom behavior.
        """
        pass

    def reply(self, content: bytes):
        """
        Send a reply to the client.
        :param content: The content to send to the client.
        """
        self.client_writer.write(content)

    async def flush(self):
        """
        Flush the client writer buffer.
        """
        await self.client_writer.drain()
