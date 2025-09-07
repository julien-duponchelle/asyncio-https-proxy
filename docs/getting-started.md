# Getting Started

This guide will walk you through setting up and using asyncio-https-proxy to create your own HTTPS proxy server with request/response interception capabilities.

## Overview

asyncio-https-proxy is an embeddable, asyncio-based HTTPS forward proxy server that allows you to intercept, modify, and analyze HTTP and HTTPS traffic. Unlike standalone proxy servers, this library is designed to be integrated directly into your Python applications.

### Key Concepts

**HTTPS Interception**
: The proxy can intercept HTTPS traffic by acting as a man-in-the-middle. It generates certificates on-the-fly using its own Certificate Authority (CA).

**Handler-Based Architecture**
: You implement a custom handler class. For most use cases, extend [HTTPSForwardProxyHandler](reference/https_forward_proxy_handler.md) which provides automatic request forwarding. For advanced control, use the lower-level [HTTPSProxyHandler](advanced-usage.md).

**Asyncio Native**
: Built using Python's asyncio framework for high-performance, non-blocking operations.

## Prerequisites

**Python Version**
: Requires Python 3.13 or later.

**Dependencies**: `cryptography` For TLS/SSL certificate generation and handling (installed automatically)

## Installation

**Basic Installation**

Install the package using pip:

```console
pip install asyncio-https-proxy
```

## Quick Start

Here's a complete working example that creates a basic HTTPS proxy server with automatic request forwarding and response analysis.

**Step 1: Create the Handler**

First, create a custom handler that extends [HTTPSForwardProxyHandler](reference/https_forward_proxy_handler.md):

```python
import asyncio
from asyncio_https_proxy import start_proxy_server, HTTPSForwardProxyHandler, TLSStore


class LoggingProxyHandler(HTTPSForwardProxyHandler):
    """A proxy handler that automatically forwards requests and logs activity."""
    
    def __init__(self):
        super().__init__()
        self.response_size = 0
    
    async def on_request_received(self):
        """Called when a complete request has been received from the client."""
        print(f"📤 Request: {self.request.method} {self.request.url()}")
        print("   Request Headers:")
        for key, value in self.request.headers:
            print(f"     {key}: {value}")
        
        # Reset response size counter
        self.response_size = 0
        
        await self.forward_http_request()

    async def on_response_received(self):
        """Called when response headers are received from the upstream server."""
        if self.response:
            print(f"📥 Response: {self.response.status_code} {self.response.reason_phrase}")
            print("   Response Headers:")
            if self.response.headers:
                for key, value in self.response.headers:
                    print(f"     {key}: {value}")
    
    async def on_response_chunk(self, chunk: bytes) -> bytes:
        """Called for each chunk of response data."""
        self.response_size += len(chunk)
        # Could modify content here if needed
        return chunk
    
    async def on_response_complete(self):
        """Called when response forwarding is complete."""
        print(f"✅ Response complete: {self.response_size} bytes")
        print("---")
```

**Key Benefits of HTTPSForwardProxyHandler:**

- **Automatic Forwarding**: No need to implement HTTP client logic yourself
- **Zero External Dependencies**: Uses only Python's built-in asyncio and ssl modules  
- **Streaming Support**: Efficiently handles large responses and chunked encoding
- **Response Processing Hooks**: Intercept and analyze response content in real-time

**Step 2: Start the Proxy Server**

Create the main function to start your proxy:

```python
async def main():
    """Start the HTTPS proxy server."""
    
    # Configuration
    host = "127.0.0.1"
    port = 8888
    
    print(f"Starting HTTPS proxy on {host}:{port}")
    print("\nThe proxy will intercept both HTTP and HTTPS traffic.")
    print("For HTTPS, it generates certificates on-the-fly using a built-in CA.")
    
    # Initialize TLS store (creates CA certificate automatically)
    tls_store = TLSStore()
    print(f"\nGenerated CA certificate. Clients may show security warnings.")
    print("Use --insecure with curl")
    
    # Start the proxy server
    server = await start_proxy_server(
        handler_builder=lambda: LoggingProxyHandler(),
        host=host,
        port=port,
        tls_store=tls_store,
    )
    
    print(f"\nProxy server started. Test with:")
    print(f"  curl --insecure --proxy http://{host}:{port} https://httpbin.org/get")
    print("\nPress Ctrl+C to stop...")
    
    # Run the server
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down proxy server...")
        finally:
            server.close()
            await server.wait_closed()
            print("Proxy server stopped.")


if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Your Proxy

**Test HTTP Requests**

```console
curl --proxy http://127.0.0.1:8888 http://httpbin.org/get
```

Expected output shows the JSON response from httpbin.org, and your proxy will log:

```text
📤 Request: GET http://httpbin.org/get
   Request Headers:
     Host: httpbin.org
     User-Agent: curl/7.68.0
     Accept: */*
📥 Response: 200 OK
   Response Headers:
     Content-Type: application/json
     Content-Length: 312
✅ Response complete: 312 bytes
---
```

**Test HTTPS Requests**

```console
curl --insecure --proxy http://127.0.0.1:8888 https://httpbin.org/get
```

The `--insecure` flag is needed because the proxy uses a self-signed CA certificate. You should see similar output as above.

**Test with Browser**

Configure your browser to use `127.0.0.1:8888` as an HTTP proxy. You'll need to accept security warnings for HTTPS sites due to the self-signed certificates.

## Understanding the Handler Lifecycle

The `HTTPSForwardProxyHandler` has a well-defined lifecycle with automatic forwarding:

1. **Client Connection**: When a client connects, the request is automatically parsed
2. **Request Processing**: `on_request_received()` is called, then automatic forwarding begins
3. **Response Headers**: `on_response_received()` is called when response headers arrive
4. **Response Body**: `on_response_chunk()` is called for each piece of response data
5. **Response Complete**: `on_response_complete()` is called when forwarding finishes

This makes it much easier to get started compared to the lower-level [HTTPSProxyHandler](advanced-usage.md).

## Common Customizations

### Content Analysis

```python
async def on_response_chunk(self, chunk: bytes) -> bytes:
    # Analyze content in real-time
    if b"error" in chunk.lower():
        print("⚠️ Error detected in response")
    return chunk
```

### Response content Modification

```python
async def on_response_chunk(self, chunk: bytes) -> bytes:
    # Replace text on the fly
    return chunk.replace(b"old_text", b"new_text")
```

### Request Blocking

```python
async def on_request_received(self):
    # Block requests to certain domains
    if "blocked.com" in self.request.host:
        self.write_response(b"HTTP/1.1 403 Forbidden\r\n\r\nBlocked")
        await self.flush_response()
        return  # Don't forward the request
    
    await self.forward_http_request()
```

## Next Steps

Now that you have a working proxy, you can:

- Implement custom request/response modification logic
- Add authentication and access control
- Integrate with logging and monitoring systems  
- Build web scraping or testing tools
- Create security analysis tools

For more advanced usage requiring complete control over request forwarding, see [Advanced Usage](advanced-usage.md).

For detailed API documentation, see the [API Reference](reference/index.md).