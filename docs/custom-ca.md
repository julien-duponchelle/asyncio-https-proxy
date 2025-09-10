# Use a custom Certificate Authority (CA)

!!! danger "Security Warning"
    When using a custom CA bundle, ensure that nobody else can access the private key of your CA certificate.
    If an attacker gains access to the private key, they could potentially intercept and decrypt your HTTPS traffic.
    This is a significant security risk, so handle the CA private key with care and trust this CA only
    in secure and controlled environments.

    Do not trust this CA in your operating system or browser, as it could compromise your security.
    Use dedicated browser instance or load the CA certificate only in specific applications
    where you need to intercept HTTPS traffic.

A certificate authority (CA) is used to sign the certificates for the domains you proxy.
By default your system's trusted CA bundle is used to validate the certificates of the target servers.

To intercept HTTPS traffic, you need to create your own CA certificate and configure your system or application
to trust this CA. This allows the proxy to generate and sign certificates for the target domains on-the-fly,
allowing it to decrypt and inspect the HTTPS traffic.


## Using Custom CA Keys with TLSStore

The `TLSStore` class can accept an existing CA private key and certificate instead of generating new ones. This is useful when you want to:

- Reuse the same CA across multiple proxy runs
- Use a pre-existing CA certificate
- Maintain certificate consistency

### Basic Usage

```python
from asyncio_https_proxy import TLSStore

# Load existing CA key and certificate from files using the proper method
tls_store = TLSStore.load_ca_from_disk("ca_private_key.pem", "ca_certificate.pem")
```

### Persisting CA to Disk

To persist a CA to disk for reuse across multiple proxy runs:

```python
from asyncio_https_proxy import TLSStore

# Create a new TLS store with explicit CA generation
tls_store = TLSStore.generate_ca(
    country="FR",
    state="Ile-de-France",
    locality="Paris",
    organization="My Company",
    common_name="My Company CA"
)

# Save the CA to disk for future use
tls_store.save_ca_to_disk("ca_private_key.pem", "ca_certificate.pem")
```

### Complete Persistence Example

```python
from asyncio_https_proxy import TLSStore
import os

# Check if CA files already exist
if os.path.exists("ca_private_key.pem") and os.path.exists("ca_certificate.pem"):
    # Load existing CA from disk
    tls_store = TLSStore.load_ca_from_disk("ca_private_key.pem", "ca_certificate.pem")
    print("Loaded existing CA from disk")
else:
    # Create new CA with explicit parameters and save it to disk
    tls_store = TLSStore.generate_ca(
        country="FR",
        state="Ile-de-France",
        locality="Paris",
        organization="My Company",
        common_name="My Company CA"
    )
    tls_store.save_ca_to_disk("ca_private_key.pem", "ca_certificate.pem")
    print("Created new CA and saved to disk")
```

### Persistent CA Example

For a complete example of creating and reusing a CA across multiple proxy runs, see [`examples/persistent_ca_usage.py`](../examples/persistent_ca_usage.py). This example demonstrates:

- Generating a CA and saving it to disk if it doesn't exist
- Loading an existing CA from disk on subsequent runs
- Proper error handling for CA file operations

```python
# Run the persistent CA example
python examples/persistent_ca_usage.py
```

The example will create `ca_private_key.pem` and `ca_certificate.pem` files in the current directory and reuse them on subsequent runs.

### Important Considerations

- Both `ca_key` and `ca_cert` parameters must be provided together or neither
- The CA key must be an EllipticCurve private key (SECP256R1)
- Store CA private keys securely and restrict file permissions appropriately
- Consider the certificate validity period when reusing CA certificates

## Usage of custom CA in your applications

### Curl

To use a custom CA bundle with curl, you can use the `--cacert` option to specify the path to your CA certificate file.

```console
curl --cacert ca_certificate.pem --proxy http://127.0.0.1:8888 https://httpbin.org/get
```