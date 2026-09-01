"""Unit tests for SHA-256 hashing and canonicalization."""

import pytest
from app.utils.hashing import canonicalise, sha256_hex, fingerprint_dict


class TestCanonicalise:
    def test_sorted_keys(self):
        result = canonicalise({"z": "1", "a": "2", "m": "3"})
        assert result == '{"a":"2","m":"3","z":"1"}'

    def test_deterministic(self):
        data = {"url": "https://example.com", "title": "Test", "snippet": "Hello"}
        assert canonicalise(data) == canonicalise(data)

    def test_whitespace_normalised(self):
        data1 = {"title": "  hello   world  "}
        data2 = {"title": "hello world"}
        assert canonicalise(data1) == canonicalise(data2)

    def test_nested_dict_sorted(self):
        data = {"outer": {"z": 1, "a": 2}}
        result = canonicalise(data)
        assert '"a":2' in result
        assert result.index('"a"') < result.index('"z"')

    def test_no_spaces_in_separators(self):
        data = {"key": "value"}
        result = canonicalise(data)
        assert ": " not in result
        assert ", " not in result

    def test_utf8_preserved(self):
        data = {"name": "José García"}
        result = canonicalise(data)
        assert "José García" in result

    def test_empty_dict(self):
        assert canonicalise({}) == "{}"


class TestSha256:
    def test_known_hash(self):
        # SHA-256 of empty string
        assert sha256_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_string_input(self):
        result = sha256_hex("hello")
        assert len(result) == 64
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_bytes_input(self):
        result = sha256_hex(b"hello")
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


class TestFingerprintDict:
    def test_deterministic(self):
        data = {"url": "https://example.com", "title": "Test"}
        fp1 = fingerprint_dict(data)
        fp2 = fingerprint_dict(data)
        assert fp1 == fp2

    def test_different_data_different_hash(self):
        data1 = {"url": "https://example.com", "title": "A"}
        data2 = {"url": "https://example.com", "title": "B"}
        assert fingerprint_dict(data1) != fingerprint_dict(data2)

    def test_key_order_irrelevant(self):
        data1 = {"b": "2", "a": "1"}
        data2 = {"a": "1", "b": "2"}
        assert fingerprint_dict(data1) == fingerprint_dict(data2)

    def test_whitespace_irrelevant(self):
        data1 = {"title": "hello  world"}
        data2 = {"title": "hello world"}
        assert fingerprint_dict(data1) == fingerprint_dict(data2)

    def test_returns_64_hex_chars(self):
        result = fingerprint_dict({"x": "y"})
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)
