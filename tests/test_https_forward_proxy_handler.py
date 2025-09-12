import ssl
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asyncio_https_proxy import HTTPResponse, HTTPSForwardProxyHandler
from asyncio_https_proxy.http_header import HTTPHeader
from asyncio_https_proxy.http_request import HTTPRequest


def create_mock_upstream_connection():
    """Helper function to create mock upstream connection with proper sync/async methods."""
    upstream_reader = AsyncMock()
    upstream_writer = MagicMock()  # Use MagicMock for sync methods
    upstream_writer.drain = AsyncMock()  # drain() is async
    upstream_writer.wait_closed = AsyncMock()  # wait_closed() is async
    return upstream_reader, upstream_writer


class TestHTTPSForwardProxyHandler:
    @pytest.mark.asyncio
    async def test_on_request_received_calls_forward_http_request(self):
        """Test that on_request_received calls forward_http_request."""
        handler = HTTPSForwardProxyHandler()

        with patch.object(
            handler, "forward_http_request", new_callable=AsyncMock
        ) as mock_forward:
            await handler.on_request_received()
            mock_forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_http_request(self):
        """Test handling of regular HTTP requests."""
        handler = HTTPSForwardProxyHandler()

        # Mock request
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "http"
        request.host = "example.com"
        request.port = 80
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body to return async generator
        async def mock_read_request_body():
            return
            yield  # Make it an async generator

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
                upstream_reader, upstream_writer = create_mock_upstream_connection()
                mock_open.return_value = (upstream_reader, upstream_writer)

                with patch.object(
                    handler, "_read_and_forward_response", new_callable=AsyncMock
                ):
                    await handler.forward_http_request()

                    # Verify connection was established
                    mock_open.assert_called_once_with("example.com", 80)

                    # Verify request line was written
                    upstream_writer.write.assert_any_call(b"GET /test HTTP/1.1\r\n")

                    # Verify headers were written
                    upstream_writer.write.assert_any_call(b"Host: example.com\r\n")

    @pytest.mark.asyncio
    async def test_handle_https_request(self):
        """Test handling of HTTPS requests."""
        handler = HTTPSForwardProxyHandler()

        # Mock request
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "https"
        request.host = "example.com"
        request.port = 443
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body to return async generator
        async def mock_read_request_body():
            return
            yield  # Make it an async generator

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
                upstream_reader, upstream_writer = create_mock_upstream_connection()
                mock_open.return_value = (upstream_reader, upstream_writer)

                with patch.object(
                    handler, "_read_and_forward_response", new_callable=AsyncMock
                ):
                    await handler.forward_http_request()

                    # Verify HTTPS connection was established with SSL
                    mock_open.assert_called_once()
                    args, kwargs = mock_open.call_args
                    assert args == ("example.com", 443)
                    assert "ssl" in kwargs

    @pytest.mark.asyncio
    async def test_read_and_forward_response(self):
        """Test reading and forwarding a response."""
        handler = HTTPSForwardProxyHandler()

        # Mock upstream reader with response data
        handler.upstream_reader = AsyncMock()
        handler.upstream_reader.readline.side_effect = [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Length: 11\r\n",
            b"\r\n",
        ]

        # Mock client writer
        handler.client_writer = AsyncMock()

        with patch.object(
            handler, "on_response_received", new_callable=AsyncMock
        ) as mock_on_response:
            with patch.object(
                handler, "_forward_response_body", new_callable=AsyncMock
            ):
                with patch.object(handler, "write_response") as mock_write:
                    await handler._read_and_forward_response()

                    # Verify response was parsed
                    assert handler.response is not None
                    assert handler.response.status_code == 200
                    assert handler.response.reason_phrase == "OK"

                    # Verify on_response_received was called
                    mock_on_response.assert_called_once()

                    # Verify status line was written
                    mock_write.assert_any_call(b"HTTP/1.1 200 OK\r\n")

    @pytest.mark.asyncio
    async def test_forward_response_body_with_content_length(self):
        """Test forwarding response body with Content-Length."""
        handler = HTTPSForwardProxyHandler()

        # Mock response with Content-Length
        handler.response = HTTPResponse()
        handler.response.headers = HTTPHeader(b"Content-Length: 11\r\n\r\n")

        # Mock upstream reader
        handler.upstream_reader = AsyncMock()
        handler.upstream_reader.read.side_effect = [b"Hello", b" World", b""]

        with patch.object(handler, "write_response") as mock_write:
            with patch.object(handler, "flush_response", new_callable=AsyncMock):
                await handler._forward_response_body()

                # Verify data was written
                mock_write.assert_any_call(b"Hello")
                mock_write.assert_any_call(b" World")

    @pytest.mark.asyncio
    async def test_forward_chunked_response(self):
        """Test forwarding chunked response."""
        handler = HTTPSForwardProxyHandler()

        # Mock response with chunked encoding
        handler.response = HTTPResponse()
        handler.response.headers = HTTPHeader(b"Transfer-Encoding: chunked\r\n\r\n")

        # Mock upstream reader for chunked data
        handler.upstream_reader = AsyncMock()
        handler.upstream_reader.readline.side_effect = [
            b"5\r\n",  # chunk size
            b"0\r\n",  # end chunk
            b"\r\n",  # final CRLF after zero chunk (no trailers)
        ]
        handler.upstream_reader.read.side_effect = [
            b"Hello",  # chunk data (5 bytes)
            b"\r\n",  # trailing CRLF after chunk data
        ]

        with patch.object(handler, "write_response") as mock_write:
            with patch.object(handler, "flush_response", new_callable=AsyncMock):
                await handler._forward_response_body()

                # Verify proper chunked format was sent: size\r\ndata\r\n0\r\n\r\n
                expected_calls = [
                    unittest.mock.call(b"5\r\n"),  # chunk size
                    unittest.mock.call(b"Hello"),  # chunk data
                    unittest.mock.call(b"\r\n"),  # chunk trailing CRLF
                    unittest.mock.call(b"0\r\n\r\n"),  # final zero chunk
                ]
                mock_write.assert_has_calls(expected_calls)

    @pytest.mark.asyncio
    async def test_error_handling_connection_failed(self):
        """Test error handling when upstream connection fails."""
        handler = HTTPSForwardProxyHandler()

        # Mock request
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "http"
        request.host = "nonexistent.com"
        request.port = 80
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: nonexistent.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body
        async def mock_read_request_body():
            return
            yield

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            with patch("asyncio.open_connection", side_effect=ConnectionRefusedError):
                with patch.object(
                    handler, "on_response_complete", new_callable=AsyncMock
                ) as mock_complete:
                    # Should raise the connection error
                    with pytest.raises(ConnectionRefusedError):
                        await handler.forward_http_request()

                    # Verify completion hook was called despite error
                    mock_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_response_chunk_called_for_content_length_response(self):
        """Test that on_response_chunk is called for content-length responses."""
        handler = HTTPSForwardProxyHandler()
        handler.upstream_reader = AsyncMock()

        # Mock response with Content-Length
        handler.response = HTTPResponse()
        handler.response.headers = HTTPHeader(b"Content-Length: 11\r\n\r\n")

        # Mock upstream reader data
        handler.upstream_reader.read.side_effect = [b"Hello", b" World", b""]

        # Track chunk calls
        chunks_received = []
        original_on_response_chunk = handler.on_response_chunk

        async def mock_on_response_chunk(chunk):
            chunks_received.append(chunk)
            return await original_on_response_chunk(chunk)

        handler.on_response_chunk = mock_on_response_chunk

        with patch.object(handler, "write_response") as mock_write:
            with patch.object(handler, "flush_response", new_callable=AsyncMock):
                with patch.object(
                    handler, "on_response_complete", new_callable=AsyncMock
                ) as mock_complete:
                    await handler._forward_response_body()

                    # Verify chunks were processed
                    assert chunks_received == [b"Hello", b" World"]

                    # Verify data was written
                    mock_write.assert_any_call(b"Hello")
                    mock_write.assert_any_call(b" World")

                    # Verify completion hook was called
                    mock_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_response_chunk_can_modify_data(self):
        """Test that on_response_chunk can modify chunk data."""
        handler = HTTPSForwardProxyHandler()
        handler.upstream_reader = AsyncMock()

        # Mock response
        handler.response = HTTPResponse()
        handler.response.headers = HTTPHeader(b"Content-Length: 5\r\n\r\n")

        handler.upstream_reader.read.side_effect = [b"Hello", b""]

        # Override on_response_chunk to modify data
        async def modify_chunk(chunk):
            return chunk.replace(b"Hello", b"Hi")

        handler.on_response_chunk = modify_chunk

        with patch.object(handler, "write_response") as mock_write:
            with patch.object(handler, "flush_response", new_callable=AsyncMock):
                with patch.object(
                    handler, "on_response_complete", new_callable=AsyncMock
                ):
                    await handler._forward_response_body()

                    # Verify modified data was written
                    mock_write.assert_called_with(b"Hi")

    @pytest.mark.asyncio
    async def test_on_response_chunk_can_filter_chunks(self):
        """Test that on_response_chunk can filter out chunks by returning None."""
        handler = HTTPSForwardProxyHandler()
        handler.upstream_reader = AsyncMock()

        # Mock response
        handler.response = HTTPResponse()
        handler.response.headers = HTTPHeader(b"Content-Length: 10\r\n\r\n")

        handler.upstream_reader.read.side_effect = [b"Hello", b"World", b""]

        # Override on_response_chunk to filter out "World"
        async def filter_chunk(chunk):
            if chunk == b"World":
                return None  # Filter out this chunk
            return chunk

        handler.on_response_chunk = filter_chunk

        with patch.object(handler, "write_response") as mock_write:
            with patch.object(handler, "flush_response", new_callable=AsyncMock):
                with patch.object(
                    handler, "on_response_complete", new_callable=AsyncMock
                ):
                    await handler._forward_response_body()

                    # Verify only "Hello" was written, "World" was filtered out
                    mock_write.assert_called_once_with(b"Hello")

    @pytest.mark.asyncio
    async def test_on_response_complete_called_after_forwarding(self):
        """Test that on_response_complete is called after response forwarding."""
        handler = HTTPSForwardProxyHandler()
        handler.upstream_reader = AsyncMock()

        # Mock response
        handler.response = HTTPResponse()
        handler.response.headers = HTTPHeader(b"Content-Length: 5\r\n\r\n")

        handler.upstream_reader.read.side_effect = [b"Hello", b""]

        with patch.object(handler, "write_response"):
            with patch.object(handler, "flush_response", new_callable=AsyncMock):
                with patch.object(
                    handler, "on_response_complete", new_callable=AsyncMock
                ) as mock_complete:
                    await handler._forward_response_body()

                    # Verify completion hook was called
                    mock_complete.assert_called_once()

                    # Verify response is marked complete
                    assert handler._response_complete is True

    @pytest.mark.asyncio
    async def test_chunked_response_only_calls_hook_for_data_chunks(self):
        """Test that chunked responses only call hook for actual data, not protocol overhead."""
        from asyncio_https_proxy.chunked_encoding import forward_chunked_response

        handler = HTTPSForwardProxyHandler()
        handler.upstream_reader = AsyncMock()

        # Mock chunked data properly
        handler.upstream_reader.readline.side_effect = [
            b"5\r\n",  # chunk size
            b"0\r\n",  # end chunk
            b"\r\n",  # final CRLF after zero chunk (no trailers)
        ]
        handler.upstream_reader.read.side_effect = [
            b"Hello",  # chunk data (5 bytes)
            b"\r\n",  # trailing CRLF after chunk data
        ]

        # Track chunk calls
        chunks_received = []
        original_on_response_chunk = handler.on_response_chunk

        async def mock_on_response_chunk(chunk):
            chunks_received.append(chunk)
            return await original_on_response_chunk(chunk)

        handler.on_response_chunk = mock_on_response_chunk

        with patch.object(handler, "write_response"):
            await forward_chunked_response(
                handler.upstream_reader,
                handler.write_response,
                handler.on_response_chunk,
            )

            # Verify only actual data was passed to hook, not protocol overhead
            assert chunks_received == [b"Hello"]

    @pytest.mark.asyncio
    async def test_response_complete_called_on_exception(self):
        """Test that on_response_complete is called even when exceptions occur."""
        handler = HTTPSForwardProxyHandler()

        # Mock request
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "http"
        request.host = "example.com"
        request.port = 80
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        with patch.object(
            handler, "read_request_body", return_value=AsyncMock()
        ) as mock_read_body:
            mock_read_body.return_value.__aiter__ = AsyncMock(return_value=iter([]))

            with patch("asyncio.open_connection", side_effect=ConnectionRefusedError):
                with patch.object(
                    handler, "on_response_complete", new_callable=AsyncMock
                ) as mock_complete:
                    with pytest.raises(ConnectionRefusedError):
                        await handler.forward_http_request()

                    # Verify completion hook was called despite exception
                    mock_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_hook_called_on_ssl_failure(self):
        """Test that on_error hook is called when SSL connection fails."""
        handler = HTTPSForwardProxyHandler()

        # Mock request for HTTPS
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "https"
        request.host = "example.com"
        request.port = 443
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body
        async def mock_read_request_body():
            return
            yield

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            with patch.object(
                handler, "on_error", new_callable=AsyncMock
            ) as mock_error:
                ssl_error = ssl.SSLError("SSL certificate verify failed")
                with patch("asyncio.open_connection", side_effect=ssl_error):
                    # Should abort request silently after calling hook
                    await handler.forward_http_request()

                    # Verify error hook was called
                    mock_error.assert_called_once_with(ssl_error)

    @pytest.mark.asyncio
    async def test_error_hook_abort(self):
        """Test that default on_error hook behavior aborts the request."""
        handler = HTTPSForwardProxyHandler()

        # Mock request for HTTPS
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "https"
        request.host = "example.com"
        request.port = 443
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body
        async def mock_read_request_body():
            return
            yield

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            ssl_error = ssl.SSLError("SSL certificate verify failed")
            with patch("asyncio.open_connection", side_effect=ssl_error):
                # Should abort request silently (no exception raised)
                await handler.forward_http_request()

    @pytest.mark.asyncio
    async def test_error_hook_not_called_for_http(self):
        """Test that error hook is not called for HTTP connection errors."""
        handler = HTTPSForwardProxyHandler()

        # Mock request for HTTP (not HTTPS)
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "http"
        request.host = "example.com"
        request.port = 80
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body
        async def mock_read_request_body():
            return
            yield

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            with patch.object(
                handler, "on_error", new_callable=AsyncMock
            ) as mock_error:
                with patch(
                    "asyncio.open_connection", side_effect=ConnectionRefusedError
                ):
                    # Should raise ConnectionRefusedError, not call error hook for SSL
                    with pytest.raises(ConnectionRefusedError):
                        await handler.forward_http_request()

                    # Verify error hook was NOT called (no SSL involved)
                    mock_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_hook_allows_custom_handling(self):
        """Test that error hook allows custom handling like logging."""

        class CustomErrorHandler(HTTPSForwardProxyHandler):
            def __init__(self):
                super().__init__()
                self.errors_logged = []

            async def on_error(self, error: Exception):
                # Custom handling: log the error
                self.errors_logged.append(str(error))

        handler = CustomErrorHandler()

        # Mock request for HTTPS
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "https"
        request.host = "example.com"
        request.port = 443
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body
        async def mock_read_request_body():
            return
            yield

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            ssl_error = ssl.SSLError("Custom SSL error")
            with patch("asyncio.open_connection", side_effect=ssl_error):
                # Should abort request silently after custom handling
                await handler.forward_http_request()

                # Verify custom handling occurred
                assert len(handler.errors_logged) == 1
                error_str = handler.errors_logged[0]
                assert "Custom SSL error" in error_str

    @pytest.mark.asyncio
    async def test_error_hook_called_on_connection_cleanup_failure(self):
        """Test that error hook is called when connection cleanup fails."""
        handler = HTTPSForwardProxyHandler()

        # Mock request for HTTPS
        request = HTTPRequest()
        request.method = "GET"
        request.scheme = "https"
        request.host = "example.com"
        request.port = 443
        request.path = "/test"
        request.version = "HTTP/1.1"
        request.headers = HTTPHeader(b"Host: example.com\r\n\r\n")
        handler.request = request

        # Mock read_request_body
        async def mock_read_request_body():
            return
            yield

        # Mock upstream connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        with patch.object(
            handler, "read_request_body", return_value=mock_read_request_body()
        ):
            with patch(
                "asyncio.open_connection", return_value=(mock_reader, mock_writer)
            ):
                with patch.object(
                    handler, "_read_and_forward_response", new_callable=AsyncMock
                ):
                    with patch.object(
                        handler, "on_error", new_callable=AsyncMock
                    ) as mock_error:
                        # Make wait_closed raise an SSL error during cleanup
                        cleanup_ssl_error = ssl.SSLError(
                            "APPLICATION_DATA_AFTER_CLOSE_NOTIFY"
                        )
                        mock_writer.wait_closed.side_effect = cleanup_ssl_error

                        # Should complete successfully despite cleanup error
                        await handler.forward_http_request()

                        # Verify error hook was called for cleanup error
                        mock_error.assert_called_once_with(cleanup_ssl_error)

                        # Verify connection was attempted to be closed
                        mock_writer.close.assert_called_once()
                        mock_writer.wait_closed.assert_called_once()
