# asyncio-https-proxy

An embeddable, asyncio-based HTTPS forward proxy server with built-in request and response interception capabilities. Designed to be integrated directly into your Python applications rather than run as a standalone service.

It's designed to be a lightweight, flexible solution for developers needing to proxy HTTP and HTTPS traffic within their applications, with full support for SSL/TLS interception. Developer keep control over the outgoing requests and responses allowing to use custom logic for modifying, logging, blocking traffic and even custom TLS fingerprinting.

The library is built using Python's asyncio framework, making it suitable for high-performance, asynchronous applications.

The library manages its own Certificate Authority (CA) to dynamically generate and sign certificates for intercepted HTTPS traffic.

It's a fundation layer for building your own proxy-based tools.

## Features

- **Embeddable**: Integrate proxy functionality directly into your Python application
- **Asyncio-native**: Built with Python's asyncio for seamless integration with async applications
- **HTTPS/SSL support**: Full SSL/TLS interception
- **Certificate generation**: Dynamically generate and sign certificates for intercepted HTTPS traffic
- **Request/Response interception**: Modify, log, or block HTTP(S) traffic in real-time
- **Lightweight**: Pure Python implementation with only cryptography as a direct external dependency

## Use Cases

- Web scraping frameworks with request modification and custom TLS fingerprinting support
- Testing frameworks with traffic interception
- Security tools and traffic analysis
- Development tools requiring HTTP(S) proxying
- Custom cache or logging solutions
- Fault injection and network simulation
- Research and educational purposes

## Quick Start

Here's a simple example to get you started:

```python
import asyncio
import httpx
from asyncio_https_proxy import start_proxy_server, HTTPSProxyHandler, TLSStore

class BasicProxyHandler(HTTPSProxyHandler):
    async def on_client_connected(self):
        print(f"Client connected: {self.request.method} {self.request.url()}")

    async def on_request_received(self):
        # Forward the request to the target server
        await self._forward_request()
    
    async def _forward_request(self):
        # Implementation details...
        pass

async def main():
    tls_store = TLSStore()
    server = await start_proxy_server(
        handler_builder=lambda: BasicProxyHandler(),
        host="127.0.0.1",
        port=8888,
        tls_store=tls_store,
    )
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

## Installation

Install the package using pip:

```console
pip install asyncio-https-proxy
```

## Getting Started

Ready to start building with asyncio-https-proxy? Check out our [Getting Started guide](getting-started.md) for detailed examples and tutorials.

For API documentation, see the [API Reference](reference/index.md).