#!/usr/bin/env python3
"""
An example of how to modify HTTP headers with asyncio-https-proxy.

This example demonstrates how to create a custom proxy handler to intercept
and modify HTTP requests before they are forwarded to the destination server.
"""

import asyncio

from asyncio_https_proxy import HTTPSForwardProxyHandler, TLSStore, start_proxy_server


class ModifyHeaderHandler(HTTPSForwardProxyHandler):
    """
    A custom proxy handler that adds a 'X-Custom-Header' to all requests.
    """

    async def on_request_received(self):
        """
        Intercept the request and add a custom header.
        """
        print(f"Original request headers for {self.request.url()}:")
        for key, value in self.request.headers:
            print(f"  {key}: {value}")

        # Add a custom header to the request
        self.request.headers.headers.append(
            ("X-Custom-Header", "Hello from the proxy!")
        )

        print("\nModified request headers:")
        for key, value in self.request.headers:
            print(f"  {key}: {value}")
        print("---")

        # Continue with the default request forwarding
        await super().on_request_received()


async def main():
    """
    Run the modifying forward proxy.
    """

    host = "127.0.0.1"
    port = 8888

    print(f"Starting HTTPS forward proxy on {host}:{port}")
    print("This proxy will add a 'X-Custom-Header' to all requests.")
    print("\nTest the proxy with:")
    print(f"  curl --insecure --proxy http://{host}:{port} https://httpbin.org/headers")
    print("\nPress Ctrl+C to stop the proxy")

    # Initialize the TLS store for HTTPS interception
    tls_store = TLSStore.generate_ca(
        country="FR",
        state="Ile-de-France",
        locality="Paris",
        organization="Modify Header Example",
        common_name="Modify Header CA",
    )

    server = await start_proxy_server(
        handler_builder=lambda: ModifyHeaderHandler(),
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
