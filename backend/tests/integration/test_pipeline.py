"""Integration tests: pipeline with mock providers, blockchain lifecycle."""

import pytest
import pytest_asyncio
from app.services.pipeline_service import PipelineService
from app.services.face_service import FaceService
from app.services.search_service import SearchService
from app.services.fingerprint_service import FingerprintService
from app.services.blockchain_service import BlockchainService
from app.services.verification_service import VerificationService
from app.providers.search.mock_provider import MockSearchProvider
from app.providers.blockchain.local_provider import LocalBlockchainProvider
from app.models.domain import SearchResult
from app.utils.hashing import fingerprint_dict


@pytest.fixture
def local_blockchain():
    return LocalBlockchainProvider()


@pytest.fixture
def mock_search():
    return MockSearchProvider()


@pytest.fixture
def fp_service():
    return FingerprintService()


@pytest.fixture
def ver_service(fp_service):
    return VerificationService(fp_service)


@pytest.mark.asyncio
async def test_blockchain_lifecycle(local_blockchain):
    """Register a fingerprint, retrieve it, and verify it."""
    fp_hex = "a" * 64
    url = "https://example.com/test"

    record = await local_blockchain.register_fingerprint(fp_hex, url)
    assert record.fingerprint == fp_hex
    assert record.network == "local"
    assert record.block_number == 1

    # Verify
    rid = local_blockchain.get_last_record_id()
    assert rid is not None

    verified = await local_blockchain.verify_fingerprint(rid, fp_hex)
    assert verified is True

    # Tampered fingerprint
    tampered = await local_blockchain.verify_fingerprint(rid, "b" * 64)
    assert tampered is False


@pytest.mark.asyncio
async def test_mock_search_returns_results(mock_search):
    results = await mock_search.search_by_image(b"fake_image_data")
    assert len(results) >= 1
    assert results[0].title != ""


@pytest.mark.asyncio
async def test_search_service_with_mock(mock_search):
    svc = SearchService(mock_search)
    response = await svc.reverse_image_search(b"fake", filename="test.jpg")
    assert response.results_found > 0
    assert response.selected_result is not None


@pytest.mark.asyncio
async def test_blockchain_service_register_and_verify(local_blockchain):
    svc = BlockchainService(local_blockchain)

    fp_hex = fingerprint_dict({"url": "https://example.com", "title": "Test"})
    record = await svc.register(fp_hex, "https://example.com")
    assert record.transaction_hash != ""

    rid = local_blockchain.get_last_record_id()
    verified = await svc.verify(rid, fp_hex)
    assert verified is True


@pytest.mark.asyncio
async def test_full_verification_flow(fp_service, ver_service, local_blockchain):
    """Full flow: create fingerprint → register → verify."""
    result = SearchResult(
        title="Test",
        url="https://example.com",
        domain="example.com",
        snippet="test",
        image_url="",
        metadata={},
    )

    fp = fp_service.create_fingerprint(result)
    bc_svc = BlockchainService(local_blockchain)
    record = await bc_svc.register(fp.value, result.url)

    verification = ver_service.verify(
        canonical_data=fp.canonical_data,
        on_chain_fingerprint=record.fingerprint,
        transaction_hash=record.transaction_hash,
    )
    assert verification.verified is True
    assert verification.status == "VERIFIED"


@pytest.mark.asyncio
async def test_tampering_detection(fp_service, ver_service, local_blockchain):
    """Modify data after registration — should show TAMPERED."""
    result = SearchResult(
        title="Original Title",
        url="https://example.com",
        domain="example.com",
        snippet="original",
        image_url="",
        metadata={},
    )

    fp = fp_service.create_fingerprint(result)
    bc_svc = BlockchainService(local_blockchain)
    await bc_svc.register(fp.value, result.url)

    # Tamper the data
    tampered_data = dict(fp.canonical_data)
    tampered_data["title"] = "TAMPERED TITLE"

    verification = ver_service.verify(
        canonical_data=tampered_data,
        on_chain_fingerprint=fp.value,
        transaction_hash="0xfake",
    )
    assert verification.verified is False
    assert verification.status == "TAMPERED"
