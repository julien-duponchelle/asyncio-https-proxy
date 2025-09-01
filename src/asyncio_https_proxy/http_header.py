class HTTPHeader:
    """
    Represents HTTP headers, preserving order and allowing duplicates.
    """

    def __init__(self, raw_headers: bytes):
        self.headers = []
        header_lines = raw_headers.decode().split("\r\n")
        for line in header_lines:
            if line:
                key, value = line.split(":", 1)
                self.headers.append((key.strip(), value.strip()))

    def first(self, key: str) -> str | None:
        """
        Get the first occurrence of a header by key (case-insensitive).

        Args:
            key: Header key to search for

        Returns:
            The header value or None if not found
        """
        for k, v in self.headers:
            if k.lower() == key.lower():
                return v
        return None

    def to_raw(self) -> bytes:
        """
        Convert headers back to raw bytes.

        Returns:
            Raw headers as bytes
        """
        return b"\r\n".join(f"{k}: {v}".encode() for k, v in self.headers) + b"\r\n\r\n"

    def to_dict(self) -> dict:
        """
        Convert headers to a dictionary. If multiple headers have the same key,
        only the last one is kept.

        Returns:
            Headers as a dictionary
        """
        result = {}
        for k, v in self.headers:
            result[k] = v
        return result

    def __iter__(self):
        return iter(self.headers)

    def __str__(self):
        return str(self.headers)

    def __repr__(self):
        return f"HTTPHeader({self.headers})"
