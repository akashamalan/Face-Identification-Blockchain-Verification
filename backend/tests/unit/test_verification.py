"""Unit tests for verification logic."""

import pytest
from app.services.fingerprint_service import FingerprintService
from app.services.verification_service import VerificationService
from app.models.domain import SearchResult
from app.utils.hashing import fingerprint_dict


@pytest.fixture
def fp_service():
    return FingerprintService()


@pytest.fixture
def ver_service(fp_service):
    return VerificationService(fp_service)


@pytest.fixture
def sample_result():
    return SearchResult(
        title="Test Profile",
        url="https://example.com/profile",
        domain="example.com",
        platform="",
        snippet="A test snippet",
        image_url="https://example.com/img.jpg",
        thumbnail="",
        metadata={"source": "test"},
    )


class TestFingerprintService:
    def test_creates_fingerprint(self, fp_service, sample_result):
        fp = fp_service.create_fingerprint(sample_result)
        assert fp.algorithm == "SHA-256"
        assert len(fp.value) == 64
        assert fp.canonical_data["url"] == sample_result.url

    def test_deterministic(self, fp_service, sample_result):
        fp1 = fp_service.create_fingerprint(sample_result)
        fp2 = fp_service.create_fingerprint(sample_result)
        assert fp1.value == fp2.value

    def test_different_input_different_hash(self, fp_service):
        r1 = SearchResult(title="A", url="https://a.com", domain="a.com", snippet="", image_url="", metadata={})
        r2 = SearchResult(title="B", url="https://b.com", domain="b.com", snippet="", image_url="", metadata={})
        assert fp_service.create_fingerprint(r1).value != fp_service.create_fingerprint(r2).value


class TestVerificationService:
    def test_verified_when_matching(self, ver_service, fp_service, sample_result):
        fp = fp_service.create_fingerprint(sample_result)
        result = ver_service.verify(
            canonical_data=fp.canonical_data,
            on_chain_fingerprint=fp.value,
            transaction_hash="0xabc",
        )
        assert result.verified is True
        assert result.status == "VERIFIED"
        assert result.local_fingerprint == result.on_chain_fingerprint

    def test_tampered_when_mismatched(self, ver_service, fp_service, sample_result):
        fp = fp_service.create_fingerprint(sample_result)
        result = ver_service.verify(
            canonical_data=fp.canonical_data,
            on_chain_fingerprint="0" * 64,
            transaction_hash="0xabc",
        )
        assert result.verified is False
        assert result.status == "TAMPERED"
        assert result.local_fingerprint != result.on_chain_fingerprint

    def test_tampered_when_data_changed(self, ver_service, fp_service, sample_result):
        fp = fp_service.create_fingerprint(sample_result)
        # Simulate data tampering
        tampered_data = dict(fp.canonical_data)
        tampered_data["title"] = "MODIFIED TITLE"

        result = ver_service.verify(
            canonical_data=tampered_data,
            on_chain_fingerprint=fp.value,
            transaction_hash="0xabc",
        )
        assert result.verified is False
        assert result.status == "TAMPERED"
