HTTPSProxyHandler
===================

Lifecycle
--------------------

The HTTPSProxyHandler has a well-defined lifecycle:

* Client Connection: When a client connects, on_client_connected() is called
* Request Parsing: The server parses the HTTP request and assigns it to self.request
* Request Processing: on_request_received() is called with the complete request
* Response Generation: Your handler processes the request and writes the response
* Connection Cleanup: The connection is automatically cleaned up

Methods
----------------

.. autoclass:: asyncio_https_proxy.HTTPSProxyHandler
    :members:
    :undoc-members:
