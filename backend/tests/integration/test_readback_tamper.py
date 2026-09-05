"""P0-5 verification: stage 6 must be a genuine chain read-back.

The decisive test is `test_tamper_after_registration_returns_tampered`: it runs the
real pipeline, then hand-edits ONE character of the canonical data and re-verifies
against the SAME on-chain record. If that cannot produce TAMPERED, stage 6 is fake.
"""

from __future__ import annotations

import pytest

from app.models.domain import SearchResult
from app.providers.blockchain.local_provider import LocalBlockchainProvider
from app.providers.search.mock_provider import MockSearchProvider
from app.services.blockchain_service import BlockchainService
from app.services.fingerprint_service import FingerprintService
from app.services.pipeline_service import PipelineService
from app.services.search_service import SearchService
from app.services.verification_service import VerificationService


class _StubFaceService:
    """Stands in for FaceService so these tests exercise the chain path, not the
    face engine (which is covered by its own tests and needs the 300MB model)."""

    async def detect(self, image_bytes: bytes, allow_multiple: bool = False):
        import numpy as np
        from app.models.domain import FaceData
        from app.services.face_service import FaceDetection
        return FaceDetection(
            data=FaceData(
                face_detected=True, face_count=1, embedding_generated=True,
                bbox=[0.0, 0.0, 10.0, 10.0], confidence=0.9, det_score=0.9,
                engine="stub:test", processing_time_ms=1.0,
            ),
            embedding=np.ones(512, dtype=np.float32),
        )


class _StubMatchingService:
    """Stands in for MatchingService. The mock search provider returns example.com
    URLs which are not fetchable, and stage 3's real download/encode path has its own
    coverage in test_matching.py — these tests are about the chain read-back."""

    threshold = 0.40

    async def match(self, input_embedding, results):
        from app.models.domain import CandidateEvidence, MatchingResult
        from app.utils.hashing import fingerprint_obj
        candidates = [
            CandidateEvidence(
                position=i, url=r.url, domain=r.domain, image_source="image_url",
                image_sha256=f"{i:064x}", image_bytes=100, faces_detected=1,
                similarity=0.9 if i == 0 else 0.1,
                decision="accepted" if i == 0 else "rejected_below_threshold",
                reason="stubbed",
            )
            for i, r in enumerate(results)
        ]
        for c in candidates:
            results[c.position].similarity = c.similarity
            results[c.position].match_reason = c.reason
        return MatchingResult(
            status="match", threshold=self.threshold, candidates=candidates,
            selected_position=0, best_similarity=0.9,
            matched_image_sha256=f"{0:064x}",
            audit_bundle_sha256=fingerprint_obj([c.model_dump() for c in candidates]),
            candidates_total=len(candidates), candidates_scored=len(candidates),
            candidates_skipped=0, matching_time_ms=1.0,
        ), (results[0] if results else None)


def _build(chain: LocalBlockchainProvider) -> PipelineService:
    fp = FingerprintService()
    return PipelineService(
        face_service=_StubFaceService(),
        search_service=SearchService(MockSearchProvider()),
        matching_service=_StubMatchingService(),
        fingerprint_service=fp,
        blockchain_service=BlockchainService(chain),
        verification_service=VerificationService(fp),
    )


@pytest.mark.asyncio
async def test_pipeline_verifies_against_readback_value():
    chain = LocalBlockchainProvider()
    result = await _build(chain).run(b"fake-image-bytes", filename="x.jpg")

    assert result.status == "success"
    assert result.verification.status == "VERIFIED"

    # The record must be readable back, and verification must have used that value.
    rid = result.blockchain.record_id
    assert rid, "no record_id — read-back impossible"
    assert result.on_chain_record.record_id == rid
    assert result.verification.record_id == rid
    assert result.verification.on_chain_fingerprint == result.on_chain_record.fingerprint


@pytest.mark.asyncio
async def test_tamper_after_registration_returns_tampered():
    """THE test. Register, then flip one character and re-verify against the same record."""
    chain = LocalBlockchainProvider()
    result = await _build(chain).run(b"fake-image-bytes", filename="x.jpg")
    assert result.verification.status == "VERIFIED"

    rid = result.blockchain.record_id
    canonical = dict(result.fingerprint.canonical_data)

    # Hand-edit exactly one character of the title.
    original_title = canonical["title"]
    canonical["title"] = original_title[:-1] + ("X" if original_title[-1] != "X" else "Y")
    assert canonical["title"] != original_title
    assert sum(a != b for a, b in zip(canonical["title"], original_title)) == 1

    verifier = VerificationService(FingerprintService())
    on_chain = await chain.get_record(rid)  # same record, fetched again

    tampered = verifier.verify(
        canonical_data=canonical,
        on_chain_fingerprint=on_chain.fingerprint,
        record_id=rid,
    )

    assert tampered.verified is False
    assert tampered.status == "TAMPERED"
    assert tampered.local_fingerprint != tampered.on_chain_fingerprint
    # The on-chain side must be unchanged by our tampering.
    assert tampered.on_chain_fingerprint == result.fingerprint.value


@pytest.mark.asyncio
async def test_verify_endpoint_reports_tampered(monkeypatch):
    """The /api/blockchain/verify route must reach TAMPERED via genuine read-back."""
    from fastapi.testclient import TestClient
    import app.api.dependencies as deps
    from app.main import app as fastapi_app

    chain = LocalBlockchainProvider()
    monkeypatch.setattr(deps, "_blockchain_provider", chain, raising=False)
    monkeypatch.setattr(deps, "get_blockchain_provider", lambda: chain)

    result = await _build(chain).run(b"fake-image-bytes", filename="x.jpg")
    rid = result.blockchain.record_id
    canonical = dict(result.fingerprint.canonical_data)

    client = TestClient(fastapi_app)

    # Untampered -> VERIFIED
    ok = client.post("/api/blockchain/verify", json={"record_id": rid, "post_data": canonical})
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["status"] == "VERIFIED"

    # One character changed -> TAMPERED
    canonical["title"] = canonical["title"][:-1] + "Z"
    bad = client.post("/api/blockchain/verify", json={"record_id": rid, "post_data": canonical})
    assert bad.status_code == 200, bad.text
    body = bad.json()["data"]
    assert body["status"] == "TAMPERED"
    assert body["verified"] is False
    assert body["local_fingerprint"] != body["on_chain_fingerprint"]


@pytest.mark.asyncio
async def test_pipeline_refuses_when_record_id_missing():
    """A provider that cannot supply a record_id must fail, not silently 'verify'."""
    from app.core.exceptions import VerificationError

    class _NoIdChain(LocalBlockchainProvider):
        async def register_fingerprint(self, fingerprint_hex, source_url):
            rec = await super().register_fingerprint(fingerprint_hex, source_url)
            rec.record_id = ""  # simulate the old write-only behaviour
            return rec

    with pytest.raises(VerificationError):
        await _build(_NoIdChain()).run(b"fake-image-bytes", filename="x.jpg")
