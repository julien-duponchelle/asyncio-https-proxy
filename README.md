# asyncio-https-proxy

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

## FAQ

### What is the difference with Mitmproxy?

Mitmproxy is a full-featured, standalone interactive proxy server with a rich user interface and extensive features for intercepting and modifying traffic. It is designed to be run as a separate application and does not embed directly into other applications.

Mitmproxy is a development tools it's not designed to be used for production environments.

### What is the difference with proxy.py?

Proxy.py is a lightweight, standalone HTTP proxy server, it can be extended with plugins and can be embedded into other applications. However, it is not specifically designed for embedding. ayncio-https-proxy is built from the ground up to be an embeddable component with only asyncio support.

### Can I use this in a production environment?

This library is designed for embedding into applications and can be used in production.
