from urllib.parse import urlparse
from .http_header import HTTPHeader


class HTTPRequest:
    """
    Represents an HTTP request with methods to parse the request line and headers.
    """

    host: str
    """The target host of the HTTP request."""
    port: int
    """The target port of the HTTP request."""
    scheme: str
    """The scheme of the HTTP request, either 'http' or 'https'."""
    version: str
    """The HTTP version, e.g. 'HTTP/1.1'."""
    method: str
    """The HTTP method, e.g. 'GET', 'POST', 'CONNECT'."""
    path: str
    """The path of the HTTP request, e.g. '/'."""
    headers: HTTPHeader
    """The HTTP headers as an HTTPHeader object."""

    def parse_request_line(self, request_line: bytes):
        """
        Parse the request line of an HTTP request.

        Args:
            request_line: The request line as bytes, e.g. b"GET / HTTP/1.1"
        """
        parts = request_line.decode().strip().split(" ")
        if len(parts) != 3:
            raise ValueError(f"Invalid request line: {request_line!r}")
        self.method, path, self.version = parts
        if self.method == "CONNECT":
            self.scheme = "https"
        else:
            self.scheme = "http"

        if self.method == "CONNECT":
            if ":" not in path:
                raise ValueError(f"Invalid CONNECT request line: {request_line!r}")
            self.host, port_str = path.split(":", 1)
            self.port = int(port_str)
        else:
            uri = urlparse(path)
            self.path = uri.path

    def parse_headers(self, raw_headers: bytes):
        """
        Parse raw HTTP headers from bytes.

        Args:
            raw_headers: Raw headers as bytes
        """
        self.headers = HTTPHeader(raw_headers)

    def parse_host(self):
        """
        Parse the Host header to set the host and port attributes.
        """
        host_header = self.headers.first("Host")
        if host_header is None:
            raise ValueError("Missing Host header in HTTP request")
        if ":" in host_header:
            self.host, port_str = host_header.split(":", 1)
            self.port = int(port_str)
        else:
            self.host = host_header
            if self.scheme == "https":
                self.port = 443
            else:
                self.port = 80

    def url(self) -> str:
        """
        Construct the full URL of the HTTP request.

        Returns:
            The full URL as a string
        """
        if self.port not in (80, 443):
            return f"{self.scheme}://{self.host}:{self.port}{self.path}"
        else:
            return f"{self.scheme}://{self.host}{self.path}"

    def __repr__(self):
        return f"HTTPRequest(host={self.host}, port={self.port}, scheme={self.scheme}, method={self.method}, path={self.path})"
