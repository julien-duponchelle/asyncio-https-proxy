import datetime
import ssl
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CERTIFICATE_VALIDITY_DAYS = 365 * 100


class TLSStore:
    """
    A simple in-memory TLS store that generates a CA and signs certificates for domains on the fly.
    """

    def __init__(self):
        self._ca = self._generate_ca()
        self._store = {}

    def _generate_ca(self):
        root_key = ec.generate_private_key(ec.SECP256R1())
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ile-de-France"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Paris"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Asyncio HTTPS Proxy"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Asyncio HTTPS Proxy CA"),
            ]
        )
        root_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(root_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                # Our certificate will be valid for ~10 years
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=CERTIFICATE_VALIDITY_DAYS)
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()),
                critical=False,
            )
            .sign(root_key, hashes.SHA256())
        )
        return (root_key, root_cert)

    def _generate_cert(
        self, domain
    ) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
        ee_key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ile-de-France"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Paris"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Asyncio HTTPS Proxy"),
            ]
        )
        ee_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self._ca[1].subject)
            .public_key(ee_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                # Our cert will be valid for 10 days
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=CERTIFICATE_VALIDITY_DAYS)
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName(domain),
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        ExtendedKeyUsageOID.CLIENT_AUTH,
                        ExtendedKeyUsageOID.SERVER_AUTH,
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(ee_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                    self._ca[1]
                    .extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
                    .value
                ),
                critical=False,
            )
            .sign(self._ca[0], hashes.SHA256())
        )
        return (ee_key, ee_cert)

    def get_ca_pem(self) -> bytes:
        """
        Get the CA PEM certificate.

        Returns:
            The CA certificate in PEM format.
        """
        return self._ca[1].public_bytes(serialization.Encoding.PEM)

    def get_ssl_context(self, domain: str) -> ssl.SSLContext:
        """
        Get a new SSL context for a given domain. If no certificate is found, generate a new one.

        Args:
            domain: The domain to get the certificate for.
        """
        key, cert = self._store.setdefault(domain, self._generate_cert(domain))
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Python doesn't support loading cert and key from memory https://github.com/python/cpython/issues/129216
        # so we need to write them to a temporary file
        with (
            tempfile.NamedTemporaryFile() as cert_file,
            tempfile.NamedTemporaryFile() as key_file,
        ):
            cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
            cert_file.flush()
            key_file.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
            key_file.flush()
            ssl_context.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)

        return ssl_context
