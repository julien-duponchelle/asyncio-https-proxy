import asyncio
import ssl
import tempfile

import pytest

from asyncio_https_proxy.https_proxy_handler import HTTPSProxyHandler
from asyncio_https_proxy.server import start_proxy_server


class MockProxyHandler(HTTPSProxyHandler):
    """Test implementation of HTTPSProxyHandler for integration testing"""

    def __init__(self):
        self.connected_calls = []
        self.requests = []
        self.errors = []

    async def on_client_connected(self):
        """Override to track connections and requests"""
        self.connected_calls.append(True)
        self.requests.append(self.request)

    async def on_error(self, error: Exception):
        """Override to track all errors"""
        self.errors.append(error)


@pytest.fixture(scope="module")
def tls_store():
    from asyncio_https_proxy.tls_store import TLSStore

    return TLSStore.generate_ca(
        country="FR",
        state="Ile-de-France",
        locality="Paris",
        organization="Test Org",
        common_name="Test CA",
    )


@pytest.fixture
def client_ssl_context(tls_store):
    """Create an SSL context for the client that trusts the proxy's CA"""
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    pem = tls_store.get_ca_pem()
    with tempfile.NamedTemporaryFile() as temp_cert_file:
        temp_cert_file.write(pem)
        temp_cert_file.flush()
        context.load_verify_locations(cafile=temp_cert_file.name)
    return context


@pytest.mark.asyncio
async def test_start_proxy_server(tls_store):
    """Test that the proxy server starts and returns a server instance"""

    server = await start_proxy_server(
        handler_builder=lambda: MockProxyHandler(),
        host="127.0.0.1",
        port=0,  # Let OS choose port
        tls_store=tls_store,
    )

    assert server is not None
    assert isinstance(server, asyncio.Server)

    # Clean up
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_handles_get_request(tls_store):
    """Test that the proxy can handle a GET request"""
    handler = MockProxyHandler()

    def handler_builder():
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        tls_store=tls_store,
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

        # Optionally, read response if needed (add timeout if reading)
        # Example: response = await asyncio.wait_for(reader.readline(), timeout=1)

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
async def test_proxy_handles_connect_request(tls_store, client_ssl_context):
    """Test that the proxy can handle a CONNECT request (HTTPS tunneling)"""
    handler = MockProxyHandler()

    def handler_builder():
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        tls_store=tls_store,
    )

    server_host, server_port = server.sockets[0].getsockname()

    reader, writer = await asyncio.open_connection(server_host, server_port)

    # Send HTTP CONNECT request
    request_data = b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"
    writer.write(request_data)
    await writer.drain()

    response = await asyncio.wait_for(reader.readline(), timeout=1)

    assert response == b"HTTP/1.1 200 Connection Established\r\n"
    await asyncio.wait_for(reader.readline(), timeout=1)  # Read the empty line

    # SSL/TLS handshake
    await writer.start_tls(
        client_ssl_context,
        server_hostname="example.com",
    )

    # Send the proper HTTPS request
    https_request = b"GET /secure HTTP/1.1\r\nHost: example.com\r\n\r\n"
    writer.write(https_request)
    await writer.drain()

    await asyncio.sleep(0.1)

    # Verify the handler was called with the HTTPS request
    assert len(handler.connected_calls) == 1
    assert len(handler.requests) == 1

    request = handler.requests[0]
    assert request.method == "GET"
    assert request.path == "/secure"
    assert request.scheme == "https"
    assert request.host == "example.com"
    assert request.port == 443
    assert request.version == "HTTP/1.1"

    writer.close()
    await writer.wait_closed()

    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_proxy_handles_multiple_connections(tls_store):
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
        tls_store=tls_store,
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
async def test_proxy_handles_client_disconnect(tls_store):
    """Test that the proxy handles client disconnections gracefully"""
    handler = MockProxyHandler()

    def handler_builder():
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        tls_store=tls_store,
    )

    try:
        server_host, server_port = server.sockets[0].getsockname()

        # Connect and immediately disconnect without sending data
        _, writer = await asyncio.open_connection(server_host, server_port)
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


@pytest.mark.asyncio
async def test_error_hook_called_on_client_connection_parse_error(tls_store):
    """Test that on_error hook is called when request parsing fails."""
    handler = MockProxyHandler()

    def handler_builder():
        return handler

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host="127.0.0.1",
        port=0,
        tls_store=tls_store,
    )

    try:
        server_host, server_port = server.sockets[0].getsockname()

        # Connect but immediately close without sending data
        reader, writer = await asyncio.open_connection(server_host, server_port)
        writer.close()
        await writer.wait_closed()

        # Give the server time to process the connection error
        await asyncio.sleep(0.1)

        # Verify the error hook was called
        assert len(handler.errors) == 1
        error = handler.errors[0]
        assert isinstance(error, ConnectionError)
        assert "Client disconnected before sending request line" in str(error)

        # Handler should not have been called for successful connection
        assert len(handler.connected_calls) == 0
        assert len(handler.requests) == 0

    finally:
        server.close()
        await server.wait_closed()
