from typing import AsyncIterator
import asyncio

MAX_CHUNK_SIZE = 4096


class HTTPSProxyHandler:
    """
    An instance of a connection from a client to the HTTPS proxy server

    Each new client connection will create a new instance of this class.
    
    Attributes:
        client_reader: StreamReader for reading data from the client
        client_writer: StreamWriter for writing data to the client
        request: The parsed HTTP request from the client (set by the server)
    """

    client_reader: asyncio.StreamReader
    client_writer: asyncio.StreamWriter

    async def on_client_connected(
        self,
    ):
        """
        Called when a client has connected to the proxy and sent a valid request.

        Override this method to implement custom behavior.
        """
        pass

    async def on_request_received(self):
        """
        Called when a complete request has been received from the client.

        Override this method to implement custom behavior.
        """
        pass

    async def read_request_body(self) -> AsyncIterator[bytes]:
        """
        Read the request body from the client. This is an async generator that yields chunks of the request body.

        Yields:
            Chunks of the request body as bytes.
        """
        content_length = self.request.headers.first("Content-Length")
        if content_length is None:
            return

        length = int(content_length)
        while True:
            chunk_size = min(length, MAX_CHUNK_SIZE)
            chunk = await self.client_reader.read(chunk_size)
            if not chunk:
                break
            yield chunk
            length -= len(chunk)
            if length <= 0:
                break

    def write_response(self, content: bytes):
        """
        Write response data to the client. Until `flush_response()` is called, the data may be buffered.

        Args:
            content: The content to send to the client.
        """
        self.client_writer.write(content)

    async def flush_response(self):
        """
        Flush the response data to the client.
        """
        await self.client_writer.drain()
