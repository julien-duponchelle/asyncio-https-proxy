import pytest

from asyncio_https_proxy import HTTPResponse
from asyncio_https_proxy.http_header import HTTPHeader


class TestHTTPResponse:
    def test_init_default_values(self):
        """Test that HTTPResponse initializes with default values."""
        response = HTTPResponse()

        assert response.version == ""
        assert response.status_code == 0
        assert response.reason_phrase == ""
        assert response.headers is None

    def test_parse_status_line_success(self):
        """Test parsing a successful status line."""
        response = HTTPResponse()
        response.parse_status_line(b"HTTP/1.1 200 OK")

        assert response.version == "HTTP/1.1"
        assert response.status_code == 200
        assert response.reason_phrase == "OK"

    def test_parse_status_line_no_reason_phrase(self):
        """Test parsing status line without reason phrase."""
        response = HTTPResponse()
        response.parse_status_line(b"HTTP/1.1 404")

        assert response.version == "HTTP/1.1"
        assert response.status_code == 404
        assert response.reason_phrase == ""

    def test_parse_status_line_with_spaces_in_reason(self):
        """Test parsing status line with spaces in reason phrase."""
        response = HTTPResponse()
        response.parse_status_line(b"HTTP/1.1 500 Internal Server Error")

        assert response.version == "HTTP/1.1"
        assert response.status_code == 500
        assert response.reason_phrase == "Internal Server Error"

    def test_parse_status_line_http2(self):
        """Test parsing HTTP/2 status line."""
        response = HTTPResponse()
        response.parse_status_line(b"HTTP/2 200 OK")

        assert response.version == "HTTP/2"
        assert response.status_code == 200
        assert response.reason_phrase == "OK"

    def test_parse_status_line_different_status_codes(self):
        """Test parsing various status codes."""
        test_cases = [
            (b"HTTP/1.1 100 Continue", 100, "Continue"),
            (b"HTTP/1.1 201 Created", 201, "Created"),
            (b"HTTP/1.1 301 Moved Permanently", 301, "Moved Permanently"),
            (b"HTTP/1.1 401 Unauthorized", 401, "Unauthorized"),
            (b"HTTP/1.1 404 Not Found", 404, "Not Found"),
            (b"HTTP/1.1 502 Bad Gateway", 502, "Bad Gateway"),
        ]

        for status_line_bytes, expected_code, expected_phrase in test_cases:
            response = HTTPResponse()
            response.parse_status_line(status_line_bytes)
            assert response.status_code == expected_code
            assert response.reason_phrase == expected_phrase

    def test_parse_status_line_invalid_too_few_parts(self):
        """Test parsing invalid status line with too few parts."""
        response = HTTPResponse()

        with pytest.raises(ValueError, match="Invalid status line"):
            response.parse_status_line(b"INVALID")

    def test_parse_status_line_invalid_single_part(self):
        """Test parsing invalid status line with single part."""
        response = HTTPResponse()

        with pytest.raises(ValueError, match="Invalid status line"):
            response.parse_status_line(b"HTTP/1.1")

    def test_parse_status_line_invalid_status_code(self):
        """Test parsing status line with invalid status code."""
        response = HTTPResponse()

        with pytest.raises(ValueError):
            response.parse_status_line(b"HTTP/1.1 NOT_A_NUMBER OK")

    def test_parse_status_line_with_leading_trailing_whitespace(self):
        """Test parsing status line with whitespace."""
        response = HTTPResponse()
        response.parse_status_line(b"  HTTP/1.1 200 OK  \r\n")

        assert response.version == "HTTP/1.1"
        assert response.status_code == 200
        assert response.reason_phrase == "OK"

    def test_parse_headers_success(self):
        """Test parsing response headers."""
        response = HTTPResponse()
        headers_data = b"Content-Type: application/json\r\nContent-Length: 100\r\nSet-Cookie: session=abc123"

        response.parse_headers(headers_data)

        assert response.headers is not None
        assert isinstance(response.headers, HTTPHeader)
        assert response.headers.first("Content-Type") == "application/json"
        assert response.headers.first("Content-Length") == "100"
        assert response.headers.first("Set-Cookie") == "session=abc123"

    def test_parse_headers_empty(self):
        """Test parsing empty headers."""
        response = HTTPResponse()
        response.parse_headers(b"")

        assert response.headers is not None
        assert isinstance(response.headers, HTTPHeader)

    def test_parse_headers_multiple_values(self):
        """Test parsing headers with multiple values."""
        response = HTTPResponse()
        headers_data = b"Set-Cookie: cookie1=value1\r\nSet-Cookie: cookie2=value2\r\nContent-Type: text/html"

        response.parse_headers(headers_data)

        assert response.headers is not None
        # Test that we can get the first Set-Cookie header
        assert response.headers.first("Set-Cookie") == "cookie1=value1"
        assert response.headers.first("Content-Type") == "text/html"

    def test_parse_headers_case_insensitive(self):
        """Test that header lookup is case insensitive."""
        response = HTTPResponse()
        headers_data = b"Content-Type: text/html\r\nContent-Length: 42"

        response.parse_headers(headers_data)

        assert response.headers is not None

        assert response.headers.first("content-type") == "text/html"
        assert response.headers.first("CONTENT-LENGTH") == "42"
        assert response.headers.first("Content-Type") == "text/html"

    def test_repr(self):
        """Test string representation."""
        response = HTTPResponse()
        response.status_code = 200
        response.reason_phrase = "OK"

        repr_str = repr(response)
        assert "HTTPResponse" in repr_str
        assert "200" in repr_str
        assert "OK" in repr_str

    def test_repr_no_reason_phrase(self):
        """Test string representation without reason phrase."""
        response = HTTPResponse()
        response.status_code = 404
        response.reason_phrase = ""

        repr_str = repr(response)
        assert "HTTPResponse" in repr_str
        assert "404" in repr_str

    def test_complete_response_parsing(self):
        """Test parsing a complete response."""
        response = HTTPResponse()

        # Parse status line
        response.parse_status_line(b"HTTP/1.1 200 OK")

        # Parse headers
        headers_data = (
            b"Content-Type: application/json\r\n"
            b"Content-Length: 42\r\n"
            b"Cache-Control: no-cache\r\n"
            b"Connection: close"
        )
        response.parse_headers(headers_data)

        # Verify everything is parsed correctly
        assert response.version == "HTTP/1.1"
        assert response.status_code == 200
        assert response.reason_phrase == "OK"
        assert response.headers is not None
        assert response.headers.first("Content-Type") == "application/json"
        assert response.headers.first("Content-Length") == "42"
        assert response.headers.first("Cache-Control") == "no-cache"
        assert response.headers.first("Connection") == "close"

    def test_parse_common_status_codes(self):
        """Test parsing common HTTP status codes."""
        common_statuses = [
            (b"HTTP/1.1 200 OK", 200, "OK"),
            (b"HTTP/1.1 201 Created", 201, "Created"),
            (b"HTTP/1.1 204 No Content", 204, "No Content"),
            (b"HTTP/1.1 301 Moved Permanently", 301, "Moved Permanently"),
            (b"HTTP/1.1 302 Found", 302, "Found"),
            (b"HTTP/1.1 304 Not Modified", 304, "Not Modified"),
            (b"HTTP/1.1 400 Bad Request", 400, "Bad Request"),
            (b"HTTP/1.1 401 Unauthorized", 401, "Unauthorized"),
            (b"HTTP/1.1 403 Forbidden", 403, "Forbidden"),
            (b"HTTP/1.1 404 Not Found", 404, "Not Found"),
            (b"HTTP/1.1 500 Internal Server Error", 500, "Internal Server Error"),
            (b"HTTP/1.1 502 Bad Gateway", 502, "Bad Gateway"),
            (b"HTTP/1.1 503 Service Unavailable", 503, "Service Unavailable"),
        ]

        for status_line, expected_code, expected_phrase in common_statuses:
            response = HTTPResponse()
            response.parse_status_line(status_line)
            assert response.status_code == expected_code
            assert response.reason_phrase == expected_phrase
