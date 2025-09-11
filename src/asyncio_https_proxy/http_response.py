from .http_header import HTTPHeader


class HTTPResponse:
    """
    Represents an HTTP response with methods to parse the status line and headers.
    """

    def __init__(self):
        self.version: str = ""
        """The HTTP version, e.g. 'HTTP/1.1'."""
        self.status_code: int = 0
        """The HTTP status code, e.g. 200, 404, 500."""
        self.reason_phrase: str = ""
        """The HTTP reason phrase, e.g. 'OK', 'Not Found', 'Internal Server Error'."""
        self.headers: HTTPHeader | None = None
        """The HTTP headers as an HTTPHeader object."""

    def parse_status_line(self, status_line: bytes):
        """
        Parse the status line of an HTTP response.

        Args:
            status_line: The status line as bytes, e.g. b"HTTP/1.1 200 OK"

        Raises:
            ValueError: If the status line format is invalid
        """
        parts = status_line.decode().strip().split(" ", 2)
        if len(parts) < 2:
            raise ValueError(f"Invalid status line: {status_line!r}")
        self.version = parts[0]
        self.status_code = int(parts[1])
        self.reason_phrase = parts[2] if len(parts) > 2 else ""

    def parse_headers(self, raw_headers: bytes):
        """
        Parse raw HTTP headers from bytes.

        Args:
            raw_headers: Raw headers as bytes
        """
        self.headers = HTTPHeader(raw_headers)

    def __repr__(self):
        return f"HTTPResponse(status_code={self.status_code}, reason_phrase={self.reason_phrase})"
