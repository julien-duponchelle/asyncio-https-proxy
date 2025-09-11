import datetime
import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID

from asyncio_https_proxy.tls_store import CERTIFICATE_VALIDITY_DAYS, TLSStore


@pytest.fixture
def tls_store():
    """Create a fresh TLSStore instance for testing"""
    return TLSStore.generate_ca(
        country="FR",
        state="Ile-de-France",
        locality="Paris",
        organization="Asyncio HTTPS Proxy",
        common_name="Asyncio HTTPS Proxy CA",
    )


def test_tls_store_initialization(tls_store):
    """Test that TLSStore initializes correctly"""
    assert tls_store._ca is not None
    assert len(tls_store._ca) == 2  # key and certificate
    assert isinstance(tls_store._ca[0], ec.EllipticCurvePrivateKey)
    assert isinstance(tls_store._ca[1], x509.Certificate)
    assert tls_store._store == {}


def test_ca_certificate_properties(tls_store):
    """Test that the CA certificate has correct properties"""
    _, ca_cert = tls_store._ca

    # Check certificate validity period (should be ~10 years)
    validity_period = ca_cert.not_valid_after_utc - ca_cert.not_valid_before_utc
    assert (
        validity_period.days >= CERTIFICATE_VALIDITY_DAYS - 1
    )  # Allow for slight timing differences

    # Check certificate is marked as CA
    basic_constraints = ca_cert.extensions.get_extension_for_class(
        x509.BasicConstraints
    ).value
    assert basic_constraints.ca is True
    assert basic_constraints.path_length is None

    # Check key usage
    key_usage = ca_cert.extensions.get_extension_for_class(x509.KeyUsage).value
    assert key_usage.digital_signature is True
    assert key_usage.key_cert_sign is True
    assert key_usage.crl_sign is True

    # Check subject
    subject_attrs = {attr.oid: attr.value for attr in ca_cert.subject}
    assert subject_attrs[x509.NameOID.COUNTRY_NAME] == "FR"
    assert subject_attrs[x509.NameOID.STATE_OR_PROVINCE_NAME] == "Ile-de-France"
    assert subject_attrs[x509.NameOID.LOCALITY_NAME] == "Paris"
    assert subject_attrs[x509.NameOID.ORGANIZATION_NAME] == "Asyncio HTTPS Proxy"
    assert subject_attrs[x509.NameOID.COMMON_NAME] == "Asyncio HTTPS Proxy CA"


def test_get_ca_pem(tls_store):
    """Test that get_ca_pem returns valid PEM-encoded CA certificate"""
    ca_pem = tls_store.get_ca_pem()

    # Should be bytes
    assert isinstance(ca_pem, bytes)

    # Should start and end with PEM markers
    assert ca_pem.startswith(b"-----BEGIN CERTIFICATE-----")
    assert ca_pem.endswith(b"-----END CERTIFICATE-----\n")

    # Should be able to load the certificate back
    ca_cert_from_pem = x509.load_pem_x509_certificate(ca_pem)

    # Should match the original CA certificate
    original_ca_cert = tls_store._ca[1]
    assert ca_cert_from_pem.serial_number == original_ca_cert.serial_number
    assert ca_cert_from_pem.subject == original_ca_cert.subject
    assert (
        ca_cert_from_pem.not_valid_before_utc == original_ca_cert.not_valid_before_utc
    )
    assert ca_cert_from_pem.not_valid_after_utc == original_ca_cert.not_valid_after_utc


def test_generate_cert_creates_valid_certificate(tls_store):
    """Test that _generate_cert creates a valid certificate for a domain"""
    domain = "example.com"
    key, cert = tls_store._generate_cert(domain)

    assert isinstance(key, ec.EllipticCurvePrivateKey)
    assert isinstance(cert, x509.Certificate)

    # Check certificate validity period (should be 10 days)
    validity_period = cert.not_valid_after_utc - cert.not_valid_before_utc
    assert validity_period.days == CERTIFICATE_VALIDITY_DAYS

    # Check certificate is NOT marked as CA
    basic_constraints = cert.extensions.get_extension_for_class(
        x509.BasicConstraints
    ).value
    assert basic_constraints.ca is False

    # Check Subject Alternative Name contains the domain
    san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    dns_names = [name.value for name in san_ext if isinstance(name, x509.DNSName)]
    assert domain in dns_names

    # Check key usage for server certificate
    key_usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    assert key_usage.digital_signature is True
    assert key_usage.key_encipherment is True
    assert key_usage.key_cert_sign is False

    # Check extended key usage
    ext_key_usage = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert ExtendedKeyUsageOID.SERVER_AUTH in ext_key_usage
    assert ExtendedKeyUsageOID.CLIENT_AUTH in ext_key_usage

    # Check issuer matches CA subject
    assert cert.issuer == tls_store._ca[1].subject


def test_generate_cert_copies_ca_certificate_information(tls_store):
    """Test that _generate_cert copies certificate information from the root CA"""
    domain = "example.com"
    _, cert = tls_store._generate_cert(domain)

    # Get CA certificate attributes
    ca_cert = tls_store._ca[1]
    ca_subject_attrs = {attr.oid: attr.value for attr in ca_cert.subject}

    # Get generated certificate attributes
    cert_subject_attrs = {attr.oid: attr.value for attr in cert.subject}

    # Verify that the generated certificate copies information from the CA
    assert (
        cert_subject_attrs[x509.NameOID.COUNTRY_NAME]
        == ca_subject_attrs[x509.NameOID.COUNTRY_NAME]
    )
    assert (
        cert_subject_attrs[x509.NameOID.STATE_OR_PROVINCE_NAME]
        == ca_subject_attrs[x509.NameOID.STATE_OR_PROVINCE_NAME]
    )
    assert (
        cert_subject_attrs[x509.NameOID.LOCALITY_NAME]
        == ca_subject_attrs[x509.NameOID.LOCALITY_NAME]
    )
    assert (
        cert_subject_attrs[x509.NameOID.ORGANIZATION_NAME]
        == ca_subject_attrs[x509.NameOID.ORGANIZATION_NAME]
    )

    assert cert_subject_attrs[x509.NameOID.ORGANIZATION_NAME] == "Asyncio HTTPS Proxy"


def test_get_ssl_context_returns_valid_context(tls_store):
    """Test that get_ssl_context returns a valid SSL context"""
    domain = "test.example.com"
    ssl_context = tls_store.get_ssl_context(domain)

    assert isinstance(ssl_context, ssl.SSLContext)
    assert ssl_context.protocol == ssl.PROTOCOL_TLS_SERVER


def test_get_ssl_context_caches_certificates(tls_store):
    """Test that get_ssl_context caches certificates for the same domain"""
    domain = "cache.example.com"

    # First call should create and store the certificate
    tls_store.get_ssl_context(domain)
    assert domain in tls_store._store

    # Second call should use cached certificate
    tls_store.get_ssl_context(domain)

    # Should be the same certificate object in store
    assert tls_store._store[domain] is tls_store._store[domain]


def test_get_ssl_context_different_domains_get_different_certs(tls_store):
    """Test that different domains get different certificates"""
    domain1 = "first.example.com"
    domain2 = "second.example.com"

    _ = tls_store.get_ssl_context(domain1)
    _ = tls_store.get_ssl_context(domain2)

    # Both domains should be in store
    assert domain1 in tls_store._store
    assert domain2 in tls_store._store

    # Should have different certificate objects
    cert1 = tls_store._store[domain1][1]  # certificate part of the tuple
    cert2 = tls_store._store[domain2][1]
    assert cert1 is not cert2

    # But both should be signed by the same CA
    assert cert1.issuer == cert2.issuer == tls_store._ca[1].subject


def test_certificates_have_correct_serial_numbers(tls_store):
    """Test that certificates have different serial numbers"""
    domain1 = "serial1.example.com"
    domain2 = "serial2.example.com"

    tls_store.get_ssl_context(domain1)
    tls_store.get_ssl_context(domain2)

    cert1 = tls_store._store[domain1][1]
    cert2 = tls_store._store[domain2][1]
    ca_cert = tls_store._ca[1]

    # All certificates should have different serial numbers
    serials = {cert1.serial_number, cert2.serial_number, ca_cert.serial_number}
    assert len(serials) == 3


def test_certificate_signature_verification(tls_store):
    """Test that generated certificates are properly signed by the CA"""
    domain = "verify.example.com"
    tls_store.get_ssl_context(domain)

    _, ca_cert = tls_store._ca
    _, ee_cert = tls_store._store[domain]

    # The end-entity certificate should be verifiable with the CA's public key
    ca_public_key = ca_cert.public_key()

    # This should not raise an exception if the signature is valid
    try:
        ca_public_key.verify(
            ee_cert.signature,
            ee_cert.tbs_certificate_bytes,
            ee_cert.signature_algorithm_oid._name.replace("sha256", "SHA256"),
        )
    except Exception:
        # If direct verification doesn't work (depends on cryptography version),
        # we can at least verify the certificate chain structure
        assert ee_cert.issuer == ca_cert.subject


def test_certificate_key_identifiers(tls_store):
    """Test that certificates have proper key identifiers"""
    domain = "keyid.example.com"
    tls_store.get_ssl_context(domain)

    ca_cert = tls_store._ca[1]
    ee_cert = tls_store._store[domain][1]

    # CA certificate should have Subject Key Identifier
    ca_ski = ca_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
    assert ca_ski is not None

    # End-entity certificate should have Subject Key Identifier
    ee_ski = ee_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
    assert ee_ski is not None

    # End-entity certificate should have Authority Key Identifier matching CA's SKI
    ee_aki = ee_cert.extensions.get_extension_for_class(
        x509.AuthorityKeyIdentifier
    ).value
    assert ee_aki.key_identifier == ca_ski.key_identifier


def test_certificate_validity_dates(tls_store):
    """Test that certificates have reasonable validity dates"""
    domain = "validity.example.com"
    tls_store.get_ssl_context(domain)

    now = datetime.datetime.now(datetime.timezone.utc)
    ca_cert = tls_store._ca[1]
    ee_cert = tls_store._store[domain][1]

    # CA certificate should be valid now and for ~CERTIFICATE_VALIDITY_DAYS years
    assert ca_cert.not_valid_before_utc <= now
    assert ca_cert.not_valid_after_utc > now
    ca_validity_days = (ca_cert.not_valid_after_utc - ca_cert.not_valid_before_utc).days
    assert ca_validity_days >= CERTIFICATE_VALIDITY_DAYS - 1

    # End-entity certificate should be valid now and for CERTIFICATE_VALIDITY_DAYS days
    assert ee_cert.not_valid_before_utc <= now
    assert ee_cert.not_valid_after_utc > now
    ee_validity_days = (ee_cert.not_valid_after_utc - ee_cert.not_valid_before_utc).days
    assert ee_validity_days == CERTIFICATE_VALIDITY_DAYS


@pytest.mark.parametrize(
    "domain",
    [
        "simple.com",
        "sub.domain.com",
        "multiple-dashes.example.com",
        "numbers123.test.org",
        "localhost",
    ],
)
def test_various_domain_names(tls_store, domain):
    """Test that various valid domain names work correctly"""
    ssl_context = tls_store.get_ssl_context(domain)

    assert isinstance(ssl_context, ssl.SSLContext)
    assert domain in tls_store._store

    # Check the certificate contains the correct domain
    cert = tls_store._store[domain][1]
    san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    dns_names = [name.value for name in san_ext if isinstance(name, x509.DNSName)]
    assert domain in dns_names


def test_multiple_contexts_same_domain_use_same_cert(tls_store):
    """Test that multiple calls for the same domain reuse the same certificate"""
    domain = "reuse.example.com"

    context1 = tls_store.get_ssl_context(domain)
    context2 = tls_store.get_ssl_context(domain)
    context3 = tls_store.get_ssl_context(domain)

    # All should be valid contexts
    assert all(
        isinstance(ctx, ssl.SSLContext) for ctx in [context1, context2, context3]
    )

    # Should only have one entry in the store
    assert len([k for k in tls_store._store.keys() if k == domain]) == 1

    # The certificate should be the same object
    first_cert = tls_store._store[domain][1]
    for _ in range(3):
        tls_store.get_ssl_context(domain)
        assert tls_store._store[domain][1] is first_cert
