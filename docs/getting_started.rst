Getting started
=================

.. toctree::
   :maxdepth: 2

Installation
----------------
To install the package, use pip:

.. code-block:: console

   $ pip install asyncio-https-proxy


Basic Usage
----------------

Here's a simple example of how to use the package:

First, import the necessary components:
.. code-block:: python

   import asyncio
   from asyncio_https_proxy import start_proxy_server, HTTPSProxyHandler, TLSStore


First, create a TLS store to manage your certificates:

.. code-block:: python

   tls_store = TLSStore()

Once initialized, a certificate authority (CA) certificate will be generated.
This CA certificate will be used to sign the certificates for the domains you proxy.

Next, you can create the main loop to start the proxy server:

.. code-block:: python

   async def main():
      """Run a basic HTTPS proxy server."""

      host = "127.0.0.1"
      port = 8888

      print(f"Starting HTTPS proxy on {host}:{port}")
      print("\nTest the proxy with:")
      print(f"  curl --insecure --proxy http://{host}:{port} https://httpbin.org/get")
      print(f"  curl --insecure --proxy http://{host}:{port} http://httpbin.org/get")
      print("\nPress Ctrl+C to stop the proxy")

      # Initialize the TLS store with a self-signed CA certificate
      tls_store = TLSStore()

      server = await start_proxy_server(
         handler_builder=lambda: BasicProxyHandler(),
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


Now you need to implement the `BasicProxyHandler` class that extends `HTTPSProxyHandler`.
In this example, the handler will log the incoming requests and forward them to the target server using `httpx`.

The library doesn't include the forwarding logic, so you need to implement it yourself.
This provides flexibility to handle requests as needed.

.. code-block:: python
   import httpx

   class BasicProxyHandler(HTTPSProxyHandler):
      async def client_connected(self):
         print(f"Client connected: {self.request}")
         for key, value in self.request.headers:
               print(f"  {key}: {value}")
         print("Url:", self.request.url())

         # Forward the request to the target server using httpx
         remote = httpx.AsyncClient()
         async with remote.stream(
               self.request.method,
               self.request.url(),
               headers=self.request.headers.to_dict(),
         ) as response:
               print(f"Received response: {response.status_code} {response.reason_phrase}")
               # Send the response back to the client
               self.reply(
                  f"HTTP/1.1 {response.status_code} {response.reason_phrase}\r\n".encode()
               )
               # Forward all headers from the remote response to the client
               for key, value in response.headers.items():
                  self.reply(f"{key}: {value}\r\n".encode())
               self.reply(b"\r\n")

               # Stream the response body in chunks
               async for chunk in response.aiter_bytes():
                  self.reply(chunk)

Once you have the proxy server running, you can test it using curl:

.. code-block:: console

   $ curl --insecure --proxy http://127.0.0.1:8888 https://example.com 

The usage of `--insecure` is necessary because the proxy uses a self-signed certificate otherwise curl will reject the connection.
We will cover how to trust the CA certificate in the next section.