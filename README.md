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
- **Optional implementation of forward proxy**: The implementation to forward HTTP request can be replace in order to use different HTTP client implementation

## Use Cases

- Web scraping frameworks with request modification and custom TLS fingerprinting support
- Testing frameworks with traffic interception
- Security tools and traffic analysis
- Development tools requiring HTTP(S) proxying
- Custom cache or logging solutions
- Fault injection and network simulation
- Research and educational purposes


## Documentation 

Document is available here: https://asyncio-https-proxy.readthedocs.io/en/latest/