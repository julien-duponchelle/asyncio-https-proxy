"""
Asyncio HTTPS Proxy Library

An embeddable asyncio-based HTTPS forward proxy with request/response interception.
"""

from .https_proxy_handler import HTTPSProxyHandler
from .https_forward_proxy_handler import HTTPSForwardProxyHandler
from .http_header import HTTPHeader
from .http_request import HTTPRequest
from .http_response import HTTPResponse
from .tls_store import TLSStore
from .server import start_proxy_server

__version__ = "0.1.0"
__all__ = [
    "start_proxy_server",
    "HTTPSProxyHandler",
    "HTTPSForwardProxyHandler",
    "HTTPHeader",
    "HTTPRequest",
    "HTTPResponse",
    "TLSStore",
]
