import pytest
from unittest.mock import AsyncMock
from asyncio_https_proxy.https_proxy_handler import HTTPSProxyHandler
from asyncio_https_proxy.http_request import HTTPRequest
from asyncio_https_proxy.http_header import HTTPHeader


class TestHTTPSProxyHandler:
    @pytest.mark.asyncio
    async def test_read_request_body_with_content_length(self):
        """Test reading request body with Content-Length header."""
        handler = HTTPSProxyHandler()

        # Mock the client reader
        mock_reader = AsyncMock()
        handler.client_reader = mock_reader

        # Create a mock request with Content-Length header
        request = HTTPRequest()
        request.headers = HTTPHeader(b"Content-Length: 10\r\n\r\n")
        handler.request = request

        # Mock the reader to return chunks
        mock_reader.read.side_effect = [b"hello", b"world", b""]

        # Collect the chunks
        chunks = []
        async for chunk in handler.read_request_body():
            chunks.append(chunk)

        assert chunks == [b"hello", b"world"]
        # Verify read was called with correct chunk sizes
        mock_reader.read.assert_any_call(
            10
        )  # First call with content length (min(10, 4096))
        mock_reader.read.assert_any_call(5)  # Second call with remaining length

    @pytest.mark.asyncio
    async def test_read_request_body_without_content_length(self):
        """Test reading request body without Content-Length header."""
        handler = HTTPSProxyHandler()

        # Mock the client reader
        mock_reader = AsyncMock()
        handler.client_reader = mock_reader

        # Create a mock request without Content-Length header
        request = HTTPRequest()
        request.headers = HTTPHeader(b"\r\n\r\n")
        handler.request = request

        # Collect the chunks
        chunks = []
        async for chunk in handler.read_request_body():
            chunks.append(chunk)

        assert chunks == []
        # Verify read was never called
        mock_reader.read.assert_not_called()

    @pytest.mark.asyncio
    async def test_read_request_body_zero_content_length(self):
        """Test reading request body with zero Content-Length."""
        handler = HTTPSProxyHandler()

        # Mock the client reader
        mock_reader = AsyncMock()
        handler.client_reader = mock_reader

        # Create a mock request with zero Content-Length
        request = HTTPRequest()
        request.headers = HTTPHeader(b"Content-Length: 0\r\n\r\n")
        handler.request = request

        # Mock the reader to return empty bytes for zero-length read
        mock_reader.read.return_value = b""

        # Collect the chunks
        chunks = []
        async for chunk in handler.read_request_body():
            chunks.append(chunk)

        assert chunks == []
        # Verify read was called once with 0 (min(0, 4096))
        mock_reader.read.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_read_request_body_large_content(self):
        """Test reading request body larger than MAX_CHUNK_SIZE."""
        handler = HTTPSProxyHandler()

        # Mock the client reader
        mock_reader = AsyncMock()
        handler.client_reader = mock_reader

        # Create a mock request with large Content-Length
        request = HTTPRequest()
        request.headers = HTTPHeader(
            b"Content-Length: 8192\r\n\r\n"
        )  # 2 * MAX_CHUNK_SIZE
        handler.request = request

        # Mock the reader to return large chunks
        chunk1 = b"a" * 4096
        chunk2 = b"b" * 4096
        mock_reader.read.side_effect = [chunk1, chunk2]

        # Collect the chunks
        chunks = []
        async for chunk in handler.read_request_body():
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == chunk1
        assert chunks[1] == chunk2

        # Verify read was called with correct chunk sizes
        assert mock_reader.read.call_count == 2
        mock_reader.read.assert_any_call(4096)  # MAX_CHUNK_SIZE

    @pytest.mark.asyncio
    async def test_read_request_body_client_disconnects(self):
        """Test reading request body when client disconnects early."""
        handler = HTTPSProxyHandler()

        # Mock the client reader
        mock_reader = AsyncMock()
        handler.client_reader = mock_reader

        # Create a mock request with Content-Length
        request = HTTPRequest()
        request.headers = HTTPHeader(b"Content-Length: 20\r\n\r\n")
        handler.request = request

        # Mock the reader to return data then empty (disconnect)
        mock_reader.read.side_effect = [b"hello", b""]  # Empty means EOF/disconnect

        # Collect the chunks
        chunks = []
        async for chunk in handler.read_request_body():
            chunks.append(chunk)

        assert chunks == [b"hello"]
        assert mock_reader.read.call_count == 2
