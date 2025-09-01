import asyncio
import pytest
import ssl
from unittest.mock import Mock
from asyncio_https_proxy.server import start_proxy_server
from asyncio_https_proxy.https_proxy_handler import HTTPSProxyHandler


class MockProxyHandler(HTTPSProxyHandler):
    """Test implementation of HTTPSProxyHandler for integration testing"""

    def __init__(self):
        self.connected_calls = []
        self.requests = []

    async def client_connected(self):
        """Override to track connections and requests"""
        self.connected_calls.append(True)
        self.requests.append(self.request)


@pytest.fixture
def mock_ssl_context():
    """Create a mock SSL context for testing without actual certificates"""
    return Mock(spec=ssl.SSLContext)


@pytest.mark.asyncio
async def test_start_proxy_server(mock_ssl_context):
    """Test that the proxy server starts and returns a server instance"""

    server = await start_proxy_server(
        handler_builder=lambda: MockProxyHandler(),
        host="127.0.0.1",
        port=0,  # Let OS choose port
        ssl_context=mock_ssl_context,
    )

    assert server is not None
    assert isinstance(server, asyncio.Server)

    # Clean up
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_handles_get_request(mock_ssl_context):
    """Test that the proxy can handle a GET request"""
    handler = MockProxyHandler()

    def handler_builder():
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        ssl_context=mock_ssl_context,
    )

    try:
        # Get the actual port the server is listening on
        server_host, server_port = server.sockets[0].getsockname()

        # Connect as a client and send a GET request
        reader, writer = await asyncio.open_connection(server_host, server_port)

        # Send HTTP GET request
        request_data = b"GET http://example.com/test HTTP/1.1\r\nHost: example.com\r\nUser-Agent: test-client\r\n\r\n"
        writer.write(request_data)
        await writer.drain()

        # Give the server time to process
        await asyncio.sleep(0.1)

        # Verify the handler was called
        assert len(handler.connected_calls) == 1
        assert len(handler.requests) == 1

        request = handler.requests[0]
        assert request.method == "GET"
        assert request.host == "example.com"
        assert request.version == "HTTP/1.1"

        # Clean up
        writer.close()
        await writer.wait_closed()

    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_handles_connect_request(mock_ssl_context):
    """Test that the proxy can handle a CONNECT request (HTTPS tunneling)"""
    handler = MockProxyHandler()

    def handler_builder():
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        ssl_context=mock_ssl_context,
    )

    try:
        server_host, server_port = server.sockets[0].getsockname()

        reader, writer = await asyncio.open_connection(server_host, server_port)

        # Send HTTP CONNECT request
        request_data = (
            b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"
        )
        writer.write(request_data)
        await writer.drain()

        await asyncio.sleep(0.1)

        # Verify the handler was called
        assert len(handler.connected_calls) == 1
        assert len(handler.requests) == 1

        request = handler.requests[0]
        assert request.method == "CONNECT"
        assert request.host == "example.com"
        assert request.port == 443
        assert request.version == "HTTP/1.1"

        writer.close()
        await writer.wait_closed()

    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_handles_multiple_connections(mock_ssl_context):
    """Test that the proxy can handle multiple concurrent connections"""
    handler_calls = []

    def handler_builder():
        handler = MockProxyHandler()
        handler_calls.append(handler)
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        ssl_context=mock_ssl_context,
    )

    try:
        server_host, server_port = server.sockets[0].getsockname()

        # Create multiple concurrent connections
        async def make_connection():
            reader, writer = await asyncio.open_connection(server_host, server_port)
            request_data = (
                b"GET http://example.com/test HTTP/1.1\r\nHost: example.com\r\n\r\n"
            )
            writer.write(request_data)
            await writer.drain()
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        # Make 3 concurrent connections
        await asyncio.gather(make_connection(), make_connection(), make_connection())

        # Verify multiple handlers were created
        assert len(handler_calls) == 3

        # Each handler should have been called once
        for handler in handler_calls:
            assert len(handler.connected_calls) == 1
            assert len(handler.requests) == 1

    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_handles_client_disconnect(mock_ssl_context):
    """Test that the proxy handles client disconnections gracefully"""
    handler = MockProxyHandler()

    def handler_builder():
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        ssl_context=mock_ssl_context,
    )

    try:
        server_host, server_port = server.sockets[0].getsockname()

        # Connect and immediately disconnect without sending data
        reader, writer = await asyncio.open_connection(server_host, server_port)
        writer.close()
        await writer.wait_closed()

        # Give the server time to process
        await asyncio.sleep(0.1)

        # Handler should not have been called since no data was sent
        assert len(handler.connected_calls) == 0
        assert len(handler.requests) == 0

    finally:
        server.close()
        await server.wait_closed()
