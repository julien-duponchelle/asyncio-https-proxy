import asyncio
from contextlib import closing
from asyncio_https_proxy.https_proxy_handler import HTTPSProxyHandler
from asyncio_https_proxy.http_request import HTTPRequest
import ssl
from collections.abc import Callable


async def start_proxy_server(
    handler_builder: Callable[[], HTTPSProxyHandler],
    host: str,
    port: int,
    ssl_context: ssl.SSLContext,
) -> asyncio.Server:
    """
    Start the proxy server.

    :param handler_builder: A callable that returns a new instance of HTTPSProxyHandler.
    :param host: The host to bind the server to.
    :param port: The port to bind the server to.
    :param ssl_context: The SSL context for secure connections.
    """

    def proxy_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Create a handler for incoming proxy connections.

        :raises ValueError: If the request line is too long or malformed.
        :raises ConnectionError: If the client disconnect
        :raises IncompleteReadError: If the headers are incomplete
        """
        proxy = handler_builder()

        async def handle_connection():
            with closing(writer):
                request_line = await reader.readline()
                if not request_line:
                    raise ConnectionError(
                        "Client disconnected before sending request line"
                    )
                request = HTTPRequest()
                request.parse_request_line(request_line)
                headers = await reader.readuntil(b"\r\n\r\n")
                request.parse_headers(headers)

                proxy.client_reader = reader
                proxy.client_writer = writer
                proxy.request = request
                await proxy.client_connected()

        asyncio.create_task(handle_connection())

        return proxy_handler

    return await asyncio.start_server(proxy_handler, host=host, port=port)
