from asyncio_https_proxy.http_header import HTTPHeader


def test_http_header_parsing():
    raw = b"Host: example.com\r\nUser-Agent: test\r\nAccept: */*\r\n\r\n"
    header = HTTPHeader(raw)
    assert header.headers == [
        ("Host", "example.com"),
        ("User-Agent", "test"),
        ("Accept", "*/*"),
    ]
    assert header.first("host") == "example.com"
    assert header.first("user-agent") == "test"
    assert header.first("missing") is None
    assert header.to_raw().startswith(b"Host: example.com")


def test_http_header_empty():
    header = HTTPHeader(b"\r\n")
    assert header.headers == []
    assert header.first("anything") is None
    assert header.to_raw() == b"\r\n\r\n"


def test_http_header_to_dict():
    raw = b"A: 1\r\nB: 2\r\nA: 3\r\nC: 4\r\n\r\n"
    header = HTTPHeader(raw)
    d = header.to_dict()
    # Only the last value for duplicate keys is kept
    assert d == {"A": "3", "B": "2", "C": "4"}


def test_http_header_to_raw():
    raw = b"X-Test: Value1\r\nX-Test: Value2\r\n\r\n"
    header = HTTPHeader(raw)
    assert header.to_raw() == raw


def test_http_header_iteration():
    raw = b"X: 1\r\nY: 2\r\nZ: 3\r\n\r\n"
    header = HTTPHeader(raw)
    items = list(header)
    assert items == [("X", "1"), ("Y", "2"), ("Z", "3")]


def test_http_header_str():
    raw = b"Key: Value\r\nAnother: Header\r\n\r\n"
    header = HTTPHeader(raw)
    assert str(header) == "[('Key', 'Value'), ('Another', 'Header')]"


def test_http_header_repr():
    raw = b"Key: Value\r\nAnother: Header\r\n\r\n"
    header = HTTPHeader(raw)
    assert repr(header) == "HTTPHeader([('Key', 'Value'), ('Another', 'Header')])"
