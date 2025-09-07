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

## Usage of custom CA in your applications

### Curl

To use a custom CA bundle with curl, you can use the `--cacert` option to specify the path to your CA certificate file.

```console
curl --cacert ca_certificate.pem --proxy http://127.0.0.1:8888 https://httpbin.org/get
```