#!/usr/bin/env python3
"""
Basic usage example for asyncio-https-proxy.

This example shows how to set up a simple HTTPS proxy server.
"""

import asyncio
from asyncio_https_proxy import start_proxy_server, HTTPSProxyHandler


class BasicProxyHandler(HTTPSProxyHandler):
    async def client_connected(self):
        print(f"Client connected: {self.request}")
        for key, value in self.request.headers:
            print(f"  {key}: {value}")

        self.reply(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n")
        self.reply(b"Hello from the basic HTTPS proxy!\n")
        await self.flush()


async def main():
    """Run a basic HTTPS proxy server."""

    host = "127.0.0.1"
    port = 8888

    print(f"Starting HTTPS proxy on {host}:{port}")
    print("\nTest the proxy with:")
    print(f"  curl --insecure --proxy http://{host}:{port} https://httpbin.org/get")
    print(f"  curl --insecure --proxy http://{host}:{port} http://httpbin.org/get")
    print("\nPress Ctrl+C to stop the proxy")

    def handler_builder():
        return BasicProxyHandler()

    server = await start_proxy_server(
        handler_builder=handler_builder,
        host=host,
        port=port,
        certfile="examples/cert.pem",
        keyfile="examples/key.pem",
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
