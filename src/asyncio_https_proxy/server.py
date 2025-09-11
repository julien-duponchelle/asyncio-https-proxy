import asyncio
import ssl
from contextlib import closing
from asyncio_https_proxy.https_proxy_handler import HTTPSProxyHandler
from asyncio_https_proxy.http_request import HTTPRequest
from asyncio_https_proxy.tls_store import TLSStore
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
    tls_store: TLSStore,
) -> asyncio.Server:
    """
    Start the proxy server.

    Args:
        handler_builder: A callable that returns a new instance of HTTPSProxyHandler.
        host: The host to bind the server to.
        port: The port to bind the server to.
    """

    def create_connection_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Create a handler for incoming proxy connections.

        :raises ValueError: If the request line is too long or malformed.
        :raises ConnectionError: If the client disconnect
        :raises IncompleteReadError: If the headers are incomplete
        """
        handler = handler_builder()

        async def process_client_connection():
            try:
                with closing(writer):
                    initial_request = await _parse_request(reader)

                    handler.client_reader = reader
                    handler.client_writer = writer

                    if initial_request.method == "CONNECT":
                        handler.client_writer.write(
                            b"HTTP/1.1 200 Connection Established\r\n\r\n"
                        )
                        await handler.client_writer.drain()
                        try:
                            await handler.client_writer.start_tls(
                                tls_store.get_ssl_context(initial_request.host),
                                server_hostname=initial_request.host,
                            )
                        except (
                            ssl.SSLError,
                            ConnectionResetError,
                            OSError,
                        ) as ssl_error:
                            # Call unified error hook for custom handling (logging, etc.)
                            await handler.on_error(ssl_error)
                            # Always abort the connection since SSL handshake failed
                            return

                        # Re-parse the request after TLS is established
                        request = await _parse_request(handler.client_reader)
                        request.port = initial_request.port
                        request.scheme = "https"
                        handler.request = request
                    else:
                        handler.request = initial_request
                    await handler.on_client_connected()
                    await handler.on_request_received()
            except Exception as conn_error:
                # Call unified error hook for any unhandled errors
                await handler.on_error(conn_error)
                # Continue silently - connection will be closed

        # Create task with proper exception handling
        task = asyncio.create_task(process_client_connection())

        # Add done callback to handle any unhandled exceptions
        def handle_task_exception(task):
            if task.exception() is not None:
                # Exception was already handled by the try/catch above,
                # but this prevents "Task exception was never retrieved" warnings
                pass

        task.add_done_callback(handle_task_exception)

    return await asyncio.start_server(create_connection_handler, host=host, port=port)
