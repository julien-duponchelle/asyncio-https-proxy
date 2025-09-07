#!/usr/bin/env python3
"""
Forward proxy usage example for asyncio-https-proxy.

This example shows how to use HTTPSForwardProxyHandler for automatic request forwarding
without external dependencies like httpx.
"""

import asyncio

from asyncio_https_proxy import HTTPSForwardProxyHandler, TLSStore, start_proxy_server


class LoggingForwardProxyHandler(HTTPSForwardProxyHandler):
    """Example forward proxy handler with request/response logging and content analysis."""
    
    def __init__(self):
        super().__init__()
        self.response_size = 0
        
    async def on_client_connected(self):
        print(f"Client connected: {self.request}")
        # Call parent to handle the request forwarding automatically
        await super().on_client_connected()

    async def on_request_received(self):
        print(f"Request: {self.request.method} {self.request.url()}")
        print("Request headers:")
        for key, value in self.request.headers:
            print(f"  {key}: {value}")
        
        # Reset response size counter for new request
        self.response_size = 0
        
        await super().on_request_received()

    async def on_response_received(self):
        if self.response:
            print(f"Response: {self.response.status_code} {self.response.reason_phrase}")
            print("Response headers:")
            if self.response.headers:
                for key, value in self.response.headers:
                    print(f"  {key}: {value}")
    
    async def on_response_chunk(self, chunk: bytes) -> bytes:
        """Process each response chunk - log size and analyze content."""
        chunk_size = len(chunk)
        self.response_size += chunk_size
        print(f"  Received chunk: {chunk_size} bytes, total so far: {self.response_size} bytes")        
        return chunk
    
    async def on_response_complete(self):
        """Called when response forwarding is complete."""
        print("✅ Response forwarding completed")
        print(f"   Total response size: {self.response_size} bytes")
        print(f"   Request: {self.request.method} {self.request.url()}")
        print("---")


async def main():
    """Run a simple logging forward proxy."""
    
    host = "127.0.0.1"
    port = 8888

    print(f"Starting HTTPS forward proxy on {host}:{port}")
    print("\nTest the proxy with:")
    print(f"  curl --insecure --proxy http://{host}:{port} https://httpbin.org/get")
    print(f"  curl --insecure --proxy http://{host}:{port} http://httpbin.org/get")
    print(f"  curl --insecure --proxy http://{host}:{port} https://example.com")
    print("\nPress Ctrl+C to stop the proxy")

    # Initialize the TLS store for HTTPS interception
    tls_store = TLSStore()

    server = await start_proxy_server(
        handler_builder=lambda: LoggingForwardProxyHandler(),
        host=host,
        port=port,
        tls_store=tls_store,
    )
    
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down proxy...")
            server.close()
            await server.wait_closed()
            print("Proxy shut down.")


if __name__ == "__main__":
    asyncio.run(main())