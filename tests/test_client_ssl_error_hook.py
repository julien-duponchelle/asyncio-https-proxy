"""Unit tests for unified error hook functionality."""

import ssl
import pytest
from unittest.mock import AsyncMock, MagicMock
from contextlib import closing

from asyncio_https_proxy.https_proxy_handler import HTTPSProxyHandler
from asyncio_https_proxy.http_request import HTTPRequest
from asyncio_https_proxy.http_header import HTTPHeader


class ClientSSLErrorHandler(HTTPSProxyHandler):
    """Test handler for SSL error testing."""

    def __init__(self):
        super().__init__()
        self.errors = []

    async def on_error(self, error: Exception):
        """Override to track all errors."""
        self.errors.append(error)


@pytest.mark.asyncio
async def test_server_ssl_error_handling_logic():
    """Test the server's SSL error handling logic directly."""

    # Create handler that tracks SSL errors
    handler = ClientSSLErrorHandler()

    # Mock writer and reader
    mock_writer = AsyncMock()
    mock_reader = AsyncMock()

    handler.client_writer = mock_writer
    handler.client_reader = mock_reader

    # Create initial CONNECT request
    initial_request = HTTPRequest()
    initial_request.method = "CONNECT"
    initial_request.host = "example.com"
    initial_request.port = 443
    initial_request.headers = HTTPHeader(b"Host: example.com:443\r\n\r\n")

    # Mock TLS store
    mock_tls_store = MagicMock()
    mock_ssl_context = MagicMock()
    mock_tls_store.get_ssl_context.return_value = mock_ssl_context

    # Create SSL error
    ssl_error = ssl.SSLError("Certificate verification failed")
    mock_writer.start_tls.side_effect = ssl_error

    # Simulate the server's process_client_connection logic
    async def simulate_server_logic():
        with closing(mock_writer):
            handler.client_reader = mock_reader
            handler.client_writer = mock_writer

            if initial_request.method == "CONNECT":
                handler.client_writer.write(
                    b"HTTP/1.1 200 Connection Established\r\n\r\n"
                )
                await handler.client_writer.drain()
                try:
                    await handler.client_writer.start_tls(
                        mock_tls_store.get_ssl_context(initial_request.host),
                        server_hostname=initial_request.host,
                    )
                except (ssl.SSLError, ConnectionResetError, OSError) as ssl_error:
                    # Call unified error hook for custom handling (logging, etc.)
                    await handler.on_error(ssl_error)
                    # Always abort the connection since SSL handshake failed
                    return

    # Test: SSL error hook called and connection aborted
    await simulate_server_logic()

    # Verify hook was called
    assert len(handler.errors) == 1
    error = handler.errors[0]
    assert isinstance(error, ssl.SSLError)


@pytest.mark.asyncio
async def test_server_ssl_error_handling_with_custom_logging():
    """Test that the server calls SSL error hook for custom handling."""

    class LoggingSSLHandler(ClientSSLErrorHandler):
        def __init__(self):
            super().__init__()
            self.error_messages = []

        async def on_error(self, error: Exception):
            # Custom logging
            if isinstance(error, ssl.SSLError):
                self.error_messages.append(f"SSL error: {error}")
            await super().on_error(error)

    # Create handler with custom logging
    handler = LoggingSSLHandler()

    # Mock writer and reader
    mock_writer = AsyncMock()
    mock_reader = AsyncMock()

    handler.client_writer = mock_writer
    handler.client_reader = mock_reader

    # Create initial CONNECT request
    initial_request = HTTPRequest()
    initial_request.method = "CONNECT"
    initial_request.host = "example.com"
    initial_request.port = 443
    initial_request.headers = HTTPHeader(b"Host: example.com:443\r\n\r\n")

    # Mock TLS store
    mock_tls_store = MagicMock()
    mock_ssl_context = MagicMock()
    mock_tls_store.get_ssl_context.return_value = mock_ssl_context

    # Create SSL error
    ssl_error = ssl.SSLError("Certificate verification failed")
    mock_writer.start_tls.side_effect = ssl_error

    # Simulate the server's process_client_connection logic
    async def simulate_server_logic():
        with closing(mock_writer):
            handler.client_reader = mock_reader
            handler.client_writer = mock_writer

            if initial_request.method == "CONNECT":
                handler.client_writer.write(
                    b"HTTP/1.1 200 Connection Established\r\n\r\n"
                )
                await handler.client_writer.drain()
                try:
                    await handler.client_writer.start_tls(
                        mock_tls_store.get_ssl_context(initial_request.host),
                        server_hostname=initial_request.host,
                    )
                except (ssl.SSLError, ConnectionResetError, OSError) as ssl_error:
                    # Call unified error hook for custom handling (logging, etc.)
                    await handler.on_error(ssl_error)
                    # Always abort the connection since SSL handshake failed
                    return

    # Should abort connection after calling hook
    await simulate_server_logic()

    # Verify hook was called
    assert len(handler.errors) == 1
    error = handler.errors[0]
    assert isinstance(error, ssl.SSLError)

    # Verify custom logging occurred
    assert len(handler.error_messages) == 1
    assert "SSL error:" in handler.error_messages[0]
    assert "Certificate verification failed" in handler.error_messages[0]


@pytest.mark.asyncio
async def test_default_error_hook_behavior():
    """Test that default on_error hook does nothing."""
    handler = HTTPSProxyHandler()

    ssl_error = ssl.SSLError("Test error")
    # Default hook should not raise any errors and return None
    result = await handler.on_error(ssl_error)

    # Default behavior should return None (do nothing)
    assert result is None

    connection_error = ConnectionError("Test connection error")
    # Default hook should not raise any errors and return None
    result = await handler.on_error(connection_error)

    # Default behavior should return None (do nothing)
    assert result is None
