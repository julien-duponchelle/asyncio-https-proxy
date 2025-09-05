import pytest
from asyncio_https_proxy.http_request import HTTPRequest


class TestHTTPRequest:
    def test_parse_get_request_line(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.parse_headers(b"Host: example.com:8080\r\n\r\n")
        request.parse_host()

        assert request.method == "GET"
        assert request.scheme == "http"
        assert request.path == "/path"
        assert request.host == "example.com"
        assert request.port == 8080
        assert request.version == "HTTP/1.1"

    def test_parse_connect_request_line(self):
        request = HTTPRequest()
        request.parse_request_line(b"CONNECT example.com:443 HTTP/1.1")

        assert request.method == "CONNECT"
        assert request.scheme == "https"
        assert request.host == "example.com"
        assert request.port == 443
        assert request.version == "HTTP/1.1"

    def test_invalid_request_line_too_few_parts(self):
        request = HTTPRequest()
        with pytest.raises(ValueError, match="Invalid request line"):
            request.parse_request_line(b"GET /")

    def test_invalid_request_line_too_many_parts(self):
        request = HTTPRequest()
        with pytest.raises(ValueError, match="Invalid request line"):
            request.parse_request_line(b"GET / HTTP/1.1 extra")

    def test_invalid_connect_request_no_port(self):
        request = HTTPRequest()
        with pytest.raises(ValueError, match="Invalid CONNECT request line"):
            request.parse_request_line(b"CONNECT example.com HTTP/1.1")

    def test_parse_host_missing_header(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.parse_headers(b"\r\n\r\n")

        with pytest.raises(ValueError, match="Missing Host header"):
            request.parse_host()

    def test_parse_host_with_port(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.parse_headers(b"Host: example.com:9000\r\n\r\n")
        request.parse_host()

        assert request.host == "example.com"
        assert request.port == 9000

    def test_parse_host_https_default_port(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.scheme = "https"
        request.parse_headers(b"Host: example.com\r\n\r\n")
        request.parse_host()

        assert request.host == "example.com"
        assert request.port == 443

    def test_url_method_standard_port(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.parse_headers(b"Host: example.com\r\n\r\n")
        request.parse_host()

        assert request.url() == "http://example.com/path"

    def test_url_method_custom_port(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.parse_headers(b"Host: example.com:8080\r\n\r\n")
        request.parse_host()

        assert request.url() == "http://example.com:8080/path"

    def test_url_method_https(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.scheme = "https"
        request.parse_headers(b"Host: example.com\r\n\r\n")
        request.parse_host()

        assert request.url() == "https://example.com/path"

    def test_http_request_default_port(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.parse_headers(b"Host: example.com\r\n\r\n")
        request.parse_host()

        assert request.port == 80

    def test_str_representation(self):
        request = HTTPRequest()
        request.parse_request_line(b"GET /path HTTP/1.1")
        request.parse_headers(b"Host: example.com:8080\r\n\r\n")
        request.parse_host()

        assert (
            repr(request)
            == "HTTPRequest(host=example.com, port=8080, scheme=http, method=GET, path=/path)"
        )
