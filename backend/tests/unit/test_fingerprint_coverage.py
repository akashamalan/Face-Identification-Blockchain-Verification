"""The fingerprint must cover the image bytes and the audit bundle, not just metadata.

Before stage 3 the canonical data was purely search metadata, so the on-chain record
said nothing about the actual images: you could swap the uploaded photo or the matched
photo and the fingerprint would still verify. These tests fail if that regresses.
"""

from __future__ import annotations

from app.models.domain import CandidateEvidence, MatchingResult, SearchResult
from app.services.fingerprint_service import FingerprintService
from app.utils.hashing import fingerprint_obj, sha256_hex


def _result() -> SearchResult:
    return SearchResult(
        title="Profile", url="https://example.com/p", domain="example.com",
        snippet="snip", image_url="https://example.com/i.jpg", metadata={"position": 1},
    )


def _matching(sim: float = 0.87, matched_sha: str = "aa" * 32) -> MatchingResult:
    cands = [
        CandidateEvidence(
            position=0, url="https://example.com/p", domain="example.com",
            image_source="image_url", image_sha256=matched_sha, image_bytes=10,
            faces_detected=1, similarity=sim, decision="accepted", reason="ok",
        ),
        CandidateEvidence(
            position=1, url="https://other.com/q", domain="other.com",
            image_source="image_url", image_sha256="bb" * 32, image_bytes=10,
            faces_detected=1, similarity=0.11,
            decision="rejected_below_threshold", reason="low",
        ),
    ]
    return MatchingResult(
        status="match", threshold=0.40, candidates=cands, selected_position=0,
        best_similarity=sim, matched_image_sha256=matched_sha,
        audit_bundle_sha256=fingerprint_obj([c.model_dump() for c in cands]),
        candidates_total=2, candidates_scored=2, candidates_skipped=0,
    )


class TestImageHashesAreCovered:
    def test_input_image_hash_present_and_correct(self):
        fp = FingerprintService().create_fingerprint(
            _result(), input_image_bytes=b"the-uploaded-image", matching=_matching()
        )
        assert fp.canonical_data["input_image_sha256"] == sha256_hex(b"the-uploaded-image")

    def test_different_input_image_changes_fingerprint(self):
        svc = FingerprintService()
        m = _matching()
        a = svc.create_fingerprint(_result(), input_image_bytes=b"image-A", matching=m)
        b = svc.create_fingerprint(_result(), input_image_bytes=b"image-B", matching=m)
        assert a.value != b.value, "input image bytes are not covered by the fingerprint"

    def test_different_matched_image_changes_fingerprint(self):
        svc = FingerprintService()
        a = svc.create_fingerprint(
            _result(), input_image_bytes=b"img", matching=_matching(matched_sha="aa" * 32)
        )
        b = svc.create_fingerprint(
            _result(), input_image_bytes=b"img", matching=_matching(matched_sha="cc" * 32)
        )
        assert a.value != b.value, "matched image bytes are not covered"


class TestAuditBundleIsCovered:
    def test_bundle_digest_present(self):
        m = _matching()
        fp = FingerprintService().create_fingerprint(
            _result(), input_image_bytes=b"img", matching=m
        )
        assert fp.canonical_data["audit_bundle_sha256"] == m.audit_bundle_sha256
        assert len(m.audit_bundle_sha256) == 64

    def test_changing_a_rejected_candidate_changes_the_fingerprint(self):
        """Cherry-picking check: altering a LOSING candidate must still change the hash."""
        svc = FingerprintService()
        m1 = _matching()
        base = svc.create_fingerprint(_result(), input_image_bytes=b"img", matching=m1)

        m2 = _matching()
        m2.candidates[1].similarity = 0.12  # was 0.11 — a rejected candidate
        m2.audit_bundle_sha256 = fingerprint_obj([c.model_dump() for c in m2.candidates])
        altered = svc.create_fingerprint(_result(), input_image_bytes=b"img", matching=m2)

        assert base.value != altered.value

    def test_dropping_a_candidate_changes_the_fingerprint(self):
        svc = FingerprintService()
        base = svc.create_fingerprint(_result(), input_image_bytes=b"img", matching=_matching())

        m = _matching()
        m.candidates = m.candidates[:1]  # hide the rejected one
        m.audit_bundle_sha256 = fingerprint_obj([c.model_dump() for c in m.candidates])
        pruned = svc.create_fingerprint(_result(), input_image_bytes=b"img", matching=m)

        assert base.value != pruned.value

    def test_threshold_and_similarity_are_recorded(self):
        fp = FingerprintService().create_fingerprint(
            _result(), input_image_bytes=b"img", matching=_matching(sim=0.87)
        )
        assert fp.canonical_data["match_similarity"] == 0.87
        assert fp.canonical_data["match_threshold"] == 0.40


class TestDeterminism:
    def test_same_inputs_same_fingerprint(self):
        svc = FingerprintService()
        a = svc.create_fingerprint(_result(), input_image_bytes=b"img", matching=_matching())
        b = svc.create_fingerprint(_result(), input_image_bytes=b"img", matching=_matching())
        assert a.value == b.value

    def test_backwards_compatible_without_matching(self):
        """Callers that pass no matching data still produce a stable hash."""
        svc = FingerprintService()
        a = svc.create_fingerprint(_result())
        b = svc.create_fingerprint(_result())
        assert a.value == b.value
        assert a.canonical_data["audit_bundle_sha256"] == ""
