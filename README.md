# asyncio-https-proxy

<!-- START doc -->

An embeddable, asyncio-based HTTPS forward proxy server with built-in request and response interception capabilities. Designed to be integrated directly into your Python applications rather than run as a standalone service.

It's designed to be a lightweight, flexible solution for developers needing to proxy HTTP and HTTPS traffic within their applications, with full support for SSL/TLS interception. Developer keep control over the outgoing requests and responses allowing to use custom logic for modifying, logging, blocking traffic and even custom TLS fingerprinting.

## Features

- **Embeddable**: Integrate proxy functionality directly into your Python application
- **Asyncio-native**: Built with Python's asyncio for seamless integration with async applications
- **HTTPS/SSL support**: Full SSL/TLS interception
- **Request/Response interception**: Modify, log, or block HTTP(S) traffic in real-time
- **Forward proxy**: Standard HTTP CONNECT proxy protocol support
- **Lightweight**: Pure Python implementation with no additional dependencies

## Use Cases

- Web scraping frameworks with request modification and custom TLS fingerprinting support
- Testing frameworks with traffic interception
- Security tools and traffic analysis
- Development tools requiring HTTP(S) proxying
- Custom cache or logging solutions

<!-- END doc -->
