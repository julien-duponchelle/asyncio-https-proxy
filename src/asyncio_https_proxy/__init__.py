"""
Asyncio HTTPS Proxy Library

An embeddable asyncio-based HTTPS forward proxy with request/response interception.
"""

from .https_proxy_handler import HTTPSProxyHandler
from .server import start_proxy_server

__version__ = "0.1.0"
__all__ = ["start_proxy_server", "HTTPSProxyHandler"]
