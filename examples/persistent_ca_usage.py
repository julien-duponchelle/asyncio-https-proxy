#!/usr/bin/env python3
"""
Persistent CA usage example for asyncio-https-proxy.

This example demonstrates how to create and reuse a Certificate Authority (CA) 
across multiple proxy runs. If CA files don't exist, creates a default TLSStore 
and saves its CA to disk for reuse on subsequent runs.
"""

import asyncio
from pathlib import Path

from asyncio_https_proxy import HTTPSForwardProxyHandler, TLSStore, start_proxy_server

CA_KEY_FILE = "ca_private_key.pem"
CA_CERT_FILE = "ca_certificate.pem"


def get_or_create_ca():
    """Get existing CA from disk or create a new TLSStore and persist its CA."""
    ca_files_exist = Path(CA_KEY_FILE).exists() and Path(CA_CERT_FILE).exists()
    
    if ca_files_exist:
        print("Loading existing CA from disk...")
        tls_store = TLSStore.load_ca_from_disk(CA_KEY_FILE, CA_CERT_FILE)
        print("✅ CA loaded from disk")
        return tls_store
    else:
        print("No existing CA files found.")
    
    # Create new TLSStore with default CA generation
    print("Creating new TLS store...")
    tls_store = TLSStore()
    
    # Save the generated CA to disk for future use
    print("Saving CA to disk for future reuse...")
    tls_store.save_ca_to_disk(CA_KEY_FILE, CA_CERT_FILE)
    print(f"✅ CA key saved to: {CA_KEY_FILE}")
    print(f"✅ CA certificate saved to: {CA_CERT_FILE}")
    
    return tls_store


class LoggingForwardProxyHandler(HTTPSForwardProxyHandler):
    """Example forward proxy handler with logging."""
    
    async def on_client_connected(self):
        print(f"Client connected: {self.request}")
        await super().on_client_connected()

    async def on_request_received(self):
        print(f"Request: {self.request.method} {self.request.url()}")
        await super().on_request_received()


async def main():
    """Run a proxy with persistent CA."""
    
    host = "127.0.0.1"
    port = 8888
    
    print("=" * 60)
    print("HTTPS Forward Proxy with Persistent CA")
    print("=" * 60)
    
    # Get existing CA from disk or create new TLSStore and persist its CA
    tls_store = get_or_create_ca()
    
    print(f"\nStarting HTTPS forward proxy on {host}:{port}")
    print("\nTest the proxy with:")
    print(f"  curl --cacert {CA_CERT_FILE} --proxy http://{host}:{port} https://httpbin.org/get")
    print(f"  curl --cacert {CA_CERT_FILE} --proxy http://{host}:{port} http://httpbin.org/get")
    print("\nPress Ctrl+C to stop the proxy")
    print("=" * 60)

    server = await start_proxy_server(
        handler_builder=lambda: LoggingForwardProxyHandler(),
        host=host,
        port=port,
        tls_store=tls_store,
    )
    
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down proxy...")
            server.close()
            await server.wait_closed()
            print("Proxy shut down.")


if __name__ == "__main__":
    asyncio.run(main())