Getting started
=================

.. toctree::
   :maxdepth: 2

Create the SSL context
----------------------

To intercept HTTPS traffic, you need to create an SSL context that will provide the necessary certificates.

You can create a self-signed certificate using the `openssl` command-line tool:

.. code-block:: console

    $ openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"


First, import the `ssl` module:

.. code-block:: python

    import ssl


Then, create an SSL context for a server and load your certificate and private key:

.. code-block:: python

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
