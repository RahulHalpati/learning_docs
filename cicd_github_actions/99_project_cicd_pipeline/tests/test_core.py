"""Fast, pure unit tests — the bulk of the CI test stage."""

from app.core import generate_slug, is_valid_slug, is_valid_url, normalize_url


def test_valid_urls():
    assert is_valid_url("https://example.com")
    assert is_valid_url("http://example.com/path?q=1")


def test_invalid_urls():
    assert not is_valid_url("")
    assert not is_valid_url("ftp://example.com")      # scheme not allowed
    assert not is_valid_url("javascript:alert(1)")     # no host
    assert not is_valid_url("not a url")


def test_generated_slug_is_valid_and_random():
    a, b = generate_slug(), generate_slug()
    assert is_valid_slug(a)
    assert a != b                                       # cryptographically random


def test_normalize_url_strips_trailing_slash():
    assert normalize_url(" https://example.com/ ") == "https://example.com"
    assert normalize_url("https://example.com") == "https://example.com"
