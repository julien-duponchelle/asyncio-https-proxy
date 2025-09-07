# Getting Started

This guide will walk you through setting up and using asyncio-https-proxy to create your own HTTPS proxy server with request/response interception capabilities.

## Overview

asyncio-https-proxy is an embeddable, asyncio-based HTTPS forward proxy server that allows you to intercept, modify, and analyze HTTP and HTTPS traffic. Unlike standalone proxy servers, this library is designed to be integrated directly into your Python applications.

### Key Concepts

**HTTPS Interception**
: The proxy can intercept HTTPS traffic by acting as a man-in-the-middle. It generates certificates on-the-fly using its own Certificate Authority (CA).

**Handler-Based Architecture**
: You implement a custom handler class that extends [HTTPSProxyHandler](reference/https_proxy_handler.md) to define how requests and responses are processed.

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

Here's a complete working example that creates a basic HTTPS proxy server that use HTTPX to forward requests.

**Step 1: Create the Handler**

First, create a custom handler that extends [HTTPSProxyHandler](reference/https_proxy_handler.md):

```python
import asyncio
import httpx
from asyncio_https_proxy import start_proxy_server, HTTPSProxyHandler, TLSStore


class BasicProxyHandler(HTTPSProxyHandler):
    """A basic proxy handler that forwards requests and logs activity."""
    
    async def on_client_connected(self):
        """Called when a client connects to the proxy."""
        print(f"Client connected: {self.request.method} {self.request.url()}")

    async def on_request_received(self):
        """Called when a complete request has been received from the client."""
        # Log request headers
        print("Request Headers:")
        for key, value in self.request.headers:
            print(f"  {key}: {value}")
        
        # Forward the request to the target server
        await self._forward_request()
    
    async def _forward_request(self):
        """Forward the request to the target server and relay the response."""
        # Create HTTP client for forwarding requests
        async with httpx.AsyncClient() as client:
            # Forward the request with all original headers and body
            async with client.stream(
                method=self.request.method,
                url=self.request.url(),
                headers=self.request.headers.to_dict(),
                content=self.read_request_body(),  # Stream request body
            ) as response:
                print(f"Response: {response.status_code} {response.reason_phrase}")
                
                # Send response status line
                self.write_response(
                    f"HTTP/1.1 {response.status_code} {response.reason_phrase}\\r\\n".encode()
                )
                
                # Forward response headers
                for key, value in response.headers.items():
                    self.write_response(f"{key}: {value}\\r\\n".encode())
                self.write_response(b"\\r\\n")
                
                # Stream response body
                async for chunk in response.aiter_bytes():
                    self.write_response(chunk)                        
```

The handler is where you implement the custom logic by overriding the `on_` methods.

By default no forwarding capacity is provided you need to implement your own.
This give you full control on the behaviors.


```python
self.write_response(chunk)
```

Send back to the browser/HTTP client the response.

**Step 2: Start the Proxy Server**

Create the main function to start your proxy:

```python
async def main():
    """Start the HTTPS proxy server."""
    
    # Configuration
    host = "127.0.0.1"
    port = 8888
    
    print(f"Starting HTTPS proxy on {host}:{port}")
    print("\\nThe proxy will intercept both HTTP and HTTPS traffic.")
    print("For HTTPS, it generates certificates on-the-fly using a built-in CA.")
    
    # Initialize TLS store (creates CA certificate automatically)
    tls_store = TLSStore()
    print(f"\\nGenerated CA certificate. Clients may show security warnings.")
    print("Use --insecure with curl")
    
    # Start the proxy server
    server = await start_proxy_server(
        handler_builder=lambda: BasicProxyHandler(),
        host=host,
        port=port,
        tls_store=tls_store,
    )
    
    print(f"\\nProxy server started. Test with:")
    print(f"  curl --insecure --proxy http://{host}:{port} https://httpbin.org/get")
    print("\\nPress Ctrl+C to stop...")
    
    # Run the server
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("\\nShutting down proxy server...")
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
Client connected: GET http://httpbin.org/get
Request Headers:
  Host: httpbin.org
  User-Agent: curl/7.68.0
  Accept: */*
Response: 200 OK
```

**Test HTTPS Requests**

```console
curl --insecure --proxy http://127.0.0.1:8888 https://httpbin.org/get
```

The `--insecure` flag is needed because the proxy uses a self-signed CA certificate. You should see similar output as above.

**Test with Browser**

Configure your browser to use `127.0.0.1:8888` as an HTTP proxy. You'll need to accept security warnings for HTTPS sites due to the self-signed certificates.

## Understanding the Handler Lifecycle

The `HTTPSProxyHandler` has a well-defined lifecycle:

1. **Client Connection**: When a client connects, `on_client_connected()` is called
2. **Request Parsing**: The server parses the HTTP request to [HTTPRequest](reference/http_request.md) and assigns it to `self.request`
3. **Request Processing**: `on_request_received()` is called with the complete request
4. **Response Generation**: Your handler processes the request and writes the response
5. **Connection Cleanup**: The connection is automatically cleaned up

See the [HTTPSProxyHandler](reference/https_proxy_handler.md) for more details on available methods and attributes.
And [HTTPRequest](reference/http_request.md) for request structure.

## Next Steps

Now that you have a working proxy, you can:

- Implement custom request/response modification logic
- Add authentication and access control
- Integrate with logging and monitoring systems  
- Build web scraping or testing tools
- Create security analysis tools

For more advanced usage, see the [API Reference](reference/index.md).