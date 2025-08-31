from urllib.parse import urlparse


class HTTPRequest:
    host: str
    port: int
    scheme: str
    version: str
    method: str
    # A list of (header, value) tuples to preserve order and allow duplicates
    headers: list[tuple[str, str]]

    def parse_request_line(self, request_line: bytes):
        """
        Parse the request line of an HTTP request.

        :param request_line: The request line as bytes, e.g. b"GET / HTTP/1.1"
        """
        parts = request_line.decode().strip().split(" ")
        if len(parts) != 3:
            raise ValueError(f"Invalid request line: {request_line!r}")
        self.method, path, self.version = parts
        if self.method == "CONNECT":
            self.scheme = "https"
        else:
            self.scheme = "http"

        if self.scheme == "https":
            if ":" not in path:
                raise ValueError(f"Invalid CONNECT request line: {request_line!r}")
            self.host, self.port = path.split(":")[0]
        else:
            uri = urlparse(path)
            self.host = uri.hostname
            self.port = uri.port or 80

    def parse_headers(self, raw_headers: bytes):
        """
        Parse raw HTTP headers from bytes.

        :param raw_headers: Raw headers as bytes
        """
        self.headers = []
        header_lines = raw_headers.decode().split("\r\n")
        for line in header_lines:
            if line:
                key, value = line.split(":", 1)
                self.headers.append((key.strip(), value))

    def get_first_header(self, key: str) -> str | None:
        """
        Get the first occurrence of a header by key (case-insensitive).
        """
        for k, v in self.headers:
            if k.lower() == key.lower():
                return v
        return None

    def to_raw_headers(self) -> bytes:
        """
        Convert headers back to raw bytes. Includes the final CRLF to indicate end of headers.
        This can be used when forwarding the request to the target server.

        :return: Raw headers as bytes.
        """
        return b"\r\n".join(f"{k}: {v}".encode() for k, v in self.headers) + b"\r\n\r\n"

    def __str__(self):
        return f"HTTPRequest(host={self.host}, port={self.port})"
