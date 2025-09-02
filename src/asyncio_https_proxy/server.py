import asyncio
from contextlib import closing
from asyncio_https_proxy.https_proxy_handler import HTTPSProxyHandler
from asyncio_https_proxy.http_request import HTTPRequest
import ssl
from collections.abc import Callable


async def _parse_request(reader: asyncio.StreamReader) -> HTTPRequest:
    """
    Parse an HTTP request from the given reader.

    Args:
        reader: An asyncio StreamReader to read the request from.

    Returns:
        An HTTPRequest object representing the parsed request.
    """
    request_line = await reader.readline()
    if not request_line:
        raise ConnectionError("Client disconnected before sending request line")
    request = HTTPRequest()
    request.parse_request_line(request_line)
    headers = await reader.readuntil(b"\r\n\r\n")
    request.parse_headers(headers)
    request.parse_host()
    return request


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
                initial_request = await _parse_request(reader)

                proxy.client_reader = reader
                proxy.client_writer = writer

                if initial_request.method == "CONNECT":
                    proxy.client_writer.write(
                        b"HTTP/1.1 200 Connection Established\r\n\r\n"
                    )
                    await proxy.client_writer.drain()
                    await proxy.client_writer.start_tls(
                        ssl_context, server_hostname=initial_request.host
                    )
                    # Re-parse the request after TLS is established
                    request = await _parse_request(proxy.client_reader)
                    request.port = initial_request.port
                    request.scheme = "https"
                    proxy.request = request
                else:
                    proxy.request = initial_request
                await proxy.client_connected()

        asyncio.create_task(handle_connection())

    return await asyncio.start_server(proxy_handler, host=host, port=port)
