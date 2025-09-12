"""
HTTP Chunked Transfer Encoding Module

This module provides utilities for handling HTTP/1.1 chunked transfer encoding,
which allows HTTP messages to be sent in chunks when the total content length
is not known in advance.

## How Chunked Encoding Works

In HTTP chunked transfer encoding, the message body is sent as a series of chunks:

1. **Chunk Format**: Each chunk consists of:
   - Chunk size in hexadecimal followed by CRLF
   - Chunk data
   - Trailing CRLF

2. **Example**:
   ```
   5\r\n        <- chunk size (5 bytes in hex)
   Hello\r\n    <- chunk data + trailing CRLF
   6\r\n        <- next chunk size (6 bytes)
   World!\r\n   <- chunk data + trailing CRLF
   0\r\n        <- terminating chunk (size 0)
   \r\n         <- final CRLF (no trailers)
   ```

3. **Termination**: The last chunk has size 0, followed by optional trailers
   and a final CRLF.
"""

import asyncio
from typing import AsyncIterator, Awaitable, Callable, Optional


class ChunkedReader:
    """Handles reading HTTP chunked transfer encoding."""

    def __init__(self, reader: asyncio.StreamReader):
        self.reader = reader

    async def read_chunks(self) -> AsyncIterator[bytes]:
        """
        Read chunked response data.

        Yields:
            Chunks of data as bytes.
        """
        while True:
            # Read chunk size line
            chunk_size_line = await self.reader.readline()
            if not chunk_size_line:
                break

            # Parse chunk size (hex digits before optional ';' and extensions)
            chunk_size_str = chunk_size_line.decode("ascii").strip()
            try:
                # Split on ';' to handle chunk extensions, take only the size part
                chunk_size = int(chunk_size_str.split(";")[0], 16)
            except (ValueError, UnicodeDecodeError):
                break

            if chunk_size == 0:
                # Terminating chunk - read trailers until empty line
                while True:
                    trailer = await self.reader.readline()
                    if not trailer or trailer == b"\r\n":
                        break
                break

            # Read exactly chunk_size bytes of data
            chunk_data = b""
            remaining = chunk_size
            while remaining > 0:
                data = await self.reader.read(remaining)
                if not data:
                    # Connection closed unexpectedly
                    break
                chunk_data += data
                remaining -= len(data)

            if len(chunk_data) != chunk_size:
                # Incomplete read - connection was closed
                break

            # Read the trailing CRLF after chunk data
            trailing_crlf = b""
            while len(trailing_crlf) < 2:
                data = await self.reader.read(2 - len(trailing_crlf))
                if not data:
                    break
                trailing_crlf += data

            if trailing_crlf != b"\r\n":
                # Invalid chunk format
                break

            yield chunk_data


class ChunkedWriter:
    """Handles writing HTTP chunked transfer encoding."""

    def __init__(self, write_func: Callable[[bytes], None]):
        self.write_func = write_func

    def write_chunk(self, data: bytes) -> None:
        """
        Write data as a chunked transfer encoding chunk.

        Args:
            data: The chunk data to write
        """
        if data:
            chunk_size_hex = hex(len(data))[2:].encode()  # Remove '0x' prefix
            self.write_func(chunk_size_hex + b"\r\n")
            self.write_func(data)
            self.write_func(b"\r\n")

    def write_final_chunk(self) -> None:
        self.write_func(b"0\r\n\r\n")


async def forward_chunked_response(
    reader: asyncio.StreamReader,
    write_func: Callable[[bytes], None],
    chunk_hook: Callable[[bytes], Awaitable[Optional[bytes]]],
) -> None:
    """
    Forward a chunked response from reader to writer.

    Args:
        reader: The stream reader to read from
        write_func: Function to write response data
        chunk_hook: Async function to process each chunk
    """
    chunked_reader = ChunkedReader(reader)
    chunked_writer = ChunkedWriter(write_func)

    async for chunk_data in chunked_reader.read_chunks():
        # Process chunk data through hook
        processed_chunk = await chunk_hook(chunk_data)

        if processed_chunk is not None:
            chunked_writer.write_chunk(processed_chunk)

    chunked_writer.write_final_chunk()
