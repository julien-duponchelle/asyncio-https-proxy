import datetime
import ssl
import tempfile
from pathlib import Path
from typing import Union

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CERTIFICATE_VALIDITY_DAYS = 365 * 100


class TLSStore:
    """
    A simple in-memory TLS store that signs certificates for domains on the fly using a provided CA.

    Use TLSStore.generate_ca() to create a new CA, or TLSStore.load_ca_from_disk() to load an existing one.

    Args:
        ca_key: The CA private key (must be EllipticCurve)
        ca_cert: The CA certificate
    """

    def __init__(
        self,
        ca_key: ec.EllipticCurvePrivateKey,
        ca_cert: x509.Certificate,
    ):
        """
        Initialize TLSStore with an existing CA key and certificate.

        Args:
            ca_key: The CA private key (must be EllipticCurve)
            ca_cert: The CA certificate
        """
        self._ca = (ca_key, ca_cert)
        self._store = {}

    @classmethod
    def generate_ca(
        cls,
        country: str,
        state: str,
        locality: str,
        organization: str,
        common_name: str,
    ) -> "TLSStore":
        """
        Generate a new CA and create a TLSStore instance with it.

        Args:
            country: Two-letter country code (e.g., "FR", "US")
            state: State or province name (e.g., "Ile-de-France", "California")
            locality: City or locality name (e.g., "Paris", "San Francisco")
            organization: Organization name (e.g., "My Company")
            common_name: Common name for the CA (e.g., "My Company CA")

        Returns:
            TLSStore instance with the generated CA
        """
        root_key = ec.generate_private_key(ec.SECP256R1())
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
                x509.NameAttribute(NameOID.LOCALITY_NAME, locality),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
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
        return cls(ca_key=root_key, ca_cert=root_cert)

    def _generate_cert(
        self, domain
    ) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
        ee_key = ec.generate_private_key(ec.SECP256R1())

        ca_subject = self._ca[1].subject
        ca_attrs = {attr.oid: attr.value for attr in ca_subject}

        subject = x509.Name(
            [
                x509.NameAttribute(
                    NameOID.COUNTRY_NAME, ca_attrs.get(NameOID.COUNTRY_NAME, "US")
                ),
                x509.NameAttribute(
                    NameOID.STATE_OR_PROVINCE_NAME,
                    ca_attrs.get(NameOID.STATE_OR_PROVINCE_NAME, "Unknown"),
                ),
                x509.NameAttribute(
                    NameOID.LOCALITY_NAME,
                    ca_attrs.get(NameOID.LOCALITY_NAME, "Unknown"),
                ),
                x509.NameAttribute(
                    NameOID.ORGANIZATION_NAME,
                    ca_attrs.get(NameOID.ORGANIZATION_NAME, "Unknown"),
                ),
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

    def save_ca_to_disk(
        self, key_file: Union[str, Path], cert_file: Union[str, Path]
    ) -> None:
        """
        Save the CA private key and certificate to disk files.

        Args:
            key_file: Path where to save the CA private key (PEM format)
            cert_file: Path where to save the CA certificate (PEM format)
        """
        ca_key, ca_cert = self._ca

        # Save private key to disk
        with open(key_file, "wb") as f:
            f.write(
                ca_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # Save certificate to disk
        with open(cert_file, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    @classmethod
    def load_ca_from_disk(
        cls, key_file: Union[str, Path], cert_file: Union[str, Path]
    ) -> "TLSStore":
        """
        Load CA private key and certificate from disk and create a TLSStore instance.

        Args:
            key_file: Path to the CA private key file (PEM format)
            cert_file: Path to the CA certificate file (PEM format)

        Returns:
            TLSStore instance using the loaded CA

        Raises:
            ValueError: If the key file doesn't contain an EllipticCurve private key
            FileNotFoundError: If either file doesn't exist
            ValueError: If the files cannot be parsed
        """
        # Load private key
        with open(key_file, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), password=None)

        # Verify it's an EC key
        if not isinstance(ca_key, ec.EllipticCurvePrivateKey):
            raise ValueError(
                f"CA key must be an EllipticCurve private key, got {type(ca_key)}"
            )

        # Load certificate
        with open(cert_file, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())

        return cls(ca_key=ca_key, ca_cert=ca_cert)
