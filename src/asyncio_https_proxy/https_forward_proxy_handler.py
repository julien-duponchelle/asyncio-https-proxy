import asyncio
import ssl

from .chunked_encoding import forward_chunked_response
from .http_response import HTTPResponse
from .https_proxy_handler import HTTPSProxyHandler

MAX_CHUNK_SIZE = 4096


class HTTPSForwardProxyHandler(HTTPSProxyHandler):
    """
    A forward proxy handler that implements HTTP/HTTPS proxying without external dependencies.

    This handler automatically forwards HTTP and HTTPS requests to their target destinations
    and provides hooks for intercepting and modifying requests and responses.

    Note: CONNECT method is not supported by this handler.
    """

    def __init__(self):
        super().__init__()
        self.upstream_reader: asyncio.StreamReader | None = None
        self.upstream_writer: asyncio.StreamWriter | None = None
        self.response: HTTPResponse | None = None
        self._response_complete: bool = False

    async def on_request_received(self):
        """
        Called when a complete request has been received from the client.

        Override this method to modify the request before it's forwarded.
        """
        await self.forward_http_request()

    async def on_response_received(self):
        """
        Called when a complete response has been received from the upstream server.

        Override this method to modify the response before it's sent to the client.
        """
        pass

    async def on_response_chunk(self, chunk: bytes) -> bytes | None:
        """
        Called for each chunk of response body data.

        Args:
            chunk: The response data chunk

        Returns:
            Modified chunk to forward, or None to skip this chunk
        """
        return chunk  # Default: forward unchanged

    async def on_response_complete(self):
        """
        Called when the response has been completely forwarded to the client.

        Use this to perform cleanup or logging after response completion.
        """
        pass

    async def forward_http_request(self):
        """
        Forward the request
        """
        # Reset response state for new request
        self._response_complete = False

        try:
            port = self.request.port
            if self.request.scheme == "https":
                # Create SSL context for HTTPS connections
                ssl_context = ssl.create_default_context()
                try:
                    (
                        self.upstream_reader,
                        self.upstream_writer,
                    ) = await asyncio.open_connection(
                        self.request.host, port, ssl=ssl_context
                    )
                except ssl.SSLError as ssl_error:
                    # Call unified error hook for custom handling (logging, etc.)
                    await self.on_error(ssl_error)
                    # Always abort the request since SSL connection failed
                    return
            else:
                (
                    self.upstream_reader,
                    self.upstream_writer,
                ) = await asyncio.open_connection(self.request.host, port)

            # Forward the request line
            request_line = (
                f"{self.request.method} {self.request.path} {self.request.version}\r\n"
            )
            self.upstream_writer.write(request_line.encode())

            # Forward headers
            for key, value in self.request.headers:
                header_line = f"{key}: {value}\r\n"
                self.upstream_writer.write(header_line.encode())
            self.upstream_writer.write(b"\r\n")

            # Forward request body if present
            async for chunk in self.read_request_body():
                self.upstream_writer.write(chunk)

            await self.upstream_writer.drain()

            # Read and parse the response
            await self._read_and_forward_response()
        except Exception:
            # Ensure completion hook is called even if request forwarding fails
            if not self._response_complete:
                self._response_complete = True
                await self.on_response_complete()
            raise
        finally:
            # TODO: Handle keep alive
            if self.upstream_writer:
                self.upstream_writer.close()
                try:
                    await self.upstream_writer.wait_closed()
                except (ssl.SSLError, ConnectionResetError, OSError) as close_error:
                    # Call unified error hook for cleanup errors
                    await self.on_error(close_error)
                    # Continue cleanup silently - connection is being closed anyway

    async def _read_and_forward_response(self):
        """Read the response from upstream and forward it to the client."""

        if self.upstream_reader is None:
            return

        status_line = await self.upstream_reader.readline()
        if not status_line:
            raise ConnectionError("Upstream server closed connection")

        # Parse response
        self.response = HTTPResponse()
        self.response.parse_status_line(status_line)

        # Read headers
        headers_data = b""
        while True:
            line = await self.upstream_reader.readline()
            headers_data += line
            if line == b"\r\n":
                break

        # Parse headers
        if headers_data.strip():
            self.response.parse_headers(headers_data[:-2])  # Remove final \r\n

        # Call the response received hook
        await self.on_response_received()

        # Forward status line
        self.write_response(status_line)

        # Forward headers
        if self.response.headers:
            for key, value in self.response.headers:
                self.write_response(f"{key}: {value}\r\n".encode())
        self.write_response(b"\r\n")

        # Forward response body
        await self._forward_response_body()

    async def _forward_response_body(self):
        """Forward the response body from upstream to client."""
        if self.upstream_reader is None:
            return

        try:
            content_length = None
            if self.response and self.response.headers:
                content_length_header = self.response.headers.first("Content-Length")
                if content_length_header:
                    content_length = int(content_length_header)

            if content_length is not None:
                # Fixed-length response
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(remaining, MAX_CHUNK_SIZE)
                    chunk = await self.upstream_reader.read(chunk_size)
                    if not chunk:
                        break

                    # Process chunk through hook
                    processed_chunk = await self.on_response_chunk(chunk)
                    if processed_chunk is not None:
                        self.write_response(processed_chunk)

                    remaining -= len(chunk)
            else:
                # Read until connection closes or chunked encoding
                transfer_encoding = None
                if self.response and self.response.headers:
                    transfer_encoding = self.response.headers.first("Transfer-Encoding")

                if transfer_encoding and "chunked" in transfer_encoding.lower():
                    await forward_chunked_response(
                        self.upstream_reader,
                        self.write_response,
                        self.on_response_chunk,
                    )
                else:
                    # Read until EOF
                    while True:
                        chunk = await self.upstream_reader.read(MAX_CHUNK_SIZE)
                        if not chunk:
                            break

                        # Process chunk through hook
                        processed_chunk = await self.on_response_chunk(chunk)
                        if processed_chunk is not None:
                            self.write_response(processed_chunk)

            await self.flush_response()
        finally:
            # Ensure completion hook is called even if errors occur
            if not self._response_complete:
                self._response_complete = True
                await self.on_response_complete()
