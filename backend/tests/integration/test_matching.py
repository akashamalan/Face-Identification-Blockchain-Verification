"""Stage 3 tests — candidate download, re-encoding, similarity, audit bundle.

These exercise the real download and encode path against a local HTTP server serving
real face images, so similarity is genuinely computed rather than stubbed. Uses the
InsightFace model (already cached) and never touches SerpAPI.
"""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.core.config import get_settings
from app.models.domain import SearchResult
from app.services.face_service import FaceService
from app.services.matching_service import MatchingService, cosine_similarity
from app.utils.hashing import fingerprint_obj, sha256_hex

SAMPLE = Path(__file__).resolve().parents[3] / "sample_data" / "demo_face.jpg"


# ── a local image server so downloads are real but offline ──────────────────

class _Handler(http.server.BaseHTTPRequestHandler):
    payloads: dict[str, tuple[int, bytes, str]] = {}

    def do_GET(self):  # noqa: N802
        status, body, ctype = self.payloads.get(
            self.path, (404, b"nope", "text/plain")
        )
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # silence
        pass


@pytest.fixture(scope="module")
def server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def images():
    """Real face image, a differently-processed version of it, and a non-face image."""
    original = SAMPLE.read_bytes()

    # Same person, different encoding path: re-encode as PNG at 85% scale. Not a
    # byte-identical copy, so the embedding is recomputed from different pixels.
    arr = cv2.imdecode(np.frombuffer(original, np.uint8), cv2.IMREAD_COLOR)
    small = cv2.resize(arr, None, fx=0.85, fy=0.85, interpolation=cv2.INTER_AREA)
    same_person = cv2.imencode(".png", small)[1].tobytes()

    # A flat grey rectangle — decodes fine, contains no face.
    no_face = cv2.imencode(".jpg", np.full((300, 300, 3), 127, np.uint8))[1].tobytes()

    return {"original": original, "same_person": same_person, "no_face": no_face}


@pytest.fixture(scope="module")
def input_embedding():
    svc = FaceService(get_settings())
    return svc.detect_sync(SAMPLE.read_bytes()).embedding


@pytest.fixture
def matcher():
    return MatchingService(get_settings())


# ── cosine ─────────────────────────────────────────────────────────────────

def test_cosine_properties():
    a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    assert cosine_similarity(a, a) == pytest.approx(1.0, abs=1e-6)
    assert cosine_similarity(a, -a) == pytest.approx(-1.0, abs=1e-6)
    assert cosine_similarity(a, np.zeros(3, dtype=np.float32)) == 0.0
    # magnitude-invariant: insightface embeddings are not normalised
    assert cosine_similarity(a, a * 7.0) == pytest.approx(1.0, abs=1e-6)


def test_input_embedding_is_returned_not_discarded(input_embedding):
    assert isinstance(input_embedding, np.ndarray)
    assert input_embedding.shape == (512,)
    assert float(np.linalg.norm(input_embedding)) > 0


# ── the real scoring path ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_same_person_scores_high_and_is_selected(
    server, images, input_embedding, matcher
):
    _Handler.payloads = {
        "/same.png": (200, images["same_person"], "image/png"),
    }
    results = [SearchResult(title="hit", url="https://x/1", domain="x",
                            image_url=f"{server}/same.png")]

    matching, selected = await matcher.match(input_embedding, results)

    assert selected is results[0]
    assert matching.status == "match"
    assert matching.best_similarity > matcher.threshold
    assert matching.candidates[0].decision == "accepted"
    assert matching.candidates[0].faces_detected == 1
    assert matching.candidates[0].image_sha256 == sha256_hex(images["same_person"])
    assert results[0].similarity == matching.best_similarity


@pytest.mark.asyncio
async def test_no_face_candidate_is_skipped_with_reason_not_error(
    server, images, input_embedding, matcher
):
    _Handler.payloads = {"/blank.jpg": (200, images["no_face"], "image/jpeg")}
    results = [SearchResult(title="blank", url="https://x/1", domain="x",
                            image_url=f"{server}/blank.jpg")]

    matching, selected = await matcher.match(input_embedding, results)

    assert selected is None
    assert matching.status == "no_confident_match"
    ev = matching.candidates[0]
    assert ev.decision == "skipped"
    assert "no face detected" in ev.reason
    assert ev.similarity is None
    assert ev.image_sha256  # it WAS downloaded


@pytest.mark.asyncio
async def test_missing_image_and_thumbnail_recorded_as_reason(
    input_embedding, matcher
):
    results = [SearchResult(title="bare", url="https://x/1", domain="x")]
    matching, selected = await matcher.match(input_embedding, results)

    assert selected is None
    ev = matching.candidates[0]
    assert ev.decision == "skipped"
    assert "no image_url or thumbnail" in ev.reason
    assert ev.image_source == ""


@pytest.mark.asyncio
async def test_thumbnail_fallback_is_used(server, images, input_embedding, matcher):
    _Handler.payloads = {"/thumb.png": (200, images["same_person"], "image/png")}
    results = [SearchResult(title="t", url="https://x/1", domain="x",
                            image_url="", thumbnail=f"{server}/thumb.png")]

    matching, selected = await matcher.match(input_embedding, results)
    assert matching.candidates[0].image_source == "thumbnail"
    assert selected is results[0]


@pytest.mark.asyncio
async def test_http_error_recorded_as_reason(server, input_embedding, matcher):
    _Handler.payloads = {}
    results = [SearchResult(title="gone", url="https://x/1", domain="x",
                            image_url=f"{server}/missing.jpg")]

    matching, selected = await matcher.match(input_embedding, results)
    assert selected is None
    assert "HTTP 404" in matching.candidates[0].reason


@pytest.mark.asyncio
async def test_oversize_image_is_rejected(server, input_embedding):
    settings = get_settings().model_copy(update={"MATCH_MAX_IMAGE_BYTES": 1024})
    matcher = MatchingService(settings)
    big = cv2.imencode(".jpg", np.random.randint(0, 255, (800, 800, 3), dtype=np.uint8))[1].tobytes()
    assert len(big) > 1024
    _Handler.payloads = {"/big.jpg": (200, big, "image/jpeg")}
    results = [SearchResult(title="big", url="https://x/1", domain="x",
                            image_url=f"{server}/big.jpg")]

    matching, selected = await matcher.match(input_embedding, results)
    assert selected is None
    assert "too large" in matching.candidates[0].reason


# ── selection is by similarity, NOT by search position ─────────────────────

@pytest.mark.asyncio
async def test_selection_ignores_lens_position(
    server, images, input_embedding, matcher
):
    """The real face is LAST in search order; it must still win."""
    _Handler.payloads = {
        "/blank.jpg": (200, images["no_face"], "image/jpeg"),
        "/same.png": (200, images["same_person"], "image/png"),
    }
    results = [
        SearchResult(title="lens-first", url="https://x/1", domain="x",
                     image_url=f"{server}/blank.jpg", metadata={"position": 1}),
        SearchResult(title="lens-second", url="https://x/2", domain="x",
                     image_url=f"{server}/missing.jpg", metadata={"position": 2}),
        SearchResult(title="lens-last", url="https://x/3", domain="x",
                     image_url=f"{server}/same.png", metadata={"position": 3}),
    ]

    matching, selected = await matcher.match(input_embedding, results)

    assert selected is results[2], "similarity must beat Lens position"
    assert matching.selected_position == 2
    assert matching.candidates[2].decision == "accepted"


@pytest.mark.asyncio
async def test_below_threshold_returns_no_confident_match(
    server, images, input_embedding
):
    """A real face that is NOT the input person must be rejected, not returned."""
    settings = get_settings().model_copy(update={"MATCH_THRESHOLD": 0.999})
    matcher = MatchingService(settings)
    _Handler.payloads = {"/same.png": (200, images["same_person"], "image/png")}
    results = [SearchResult(title="x", url="https://x/1", domain="x",
                            image_url=f"{server}/same.png")]

    matching, selected = await matcher.match(input_embedding, results)

    assert selected is None
    assert matching.status == "no_confident_match"
    assert matching.best_similarity is not None  # it WAS scored
    assert matching.candidates[0].decision == "rejected_below_threshold"
    assert "< threshold" in matching.candidates[0].reason


# ── the audit bundle ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_bundle_covers_every_candidate_in_search_order(
    server, images, input_embedding, matcher
):
    _Handler.payloads = {
        "/blank.jpg": (200, images["no_face"], "image/jpeg"),
        "/same.png": (200, images["same_person"], "image/png"),
    }
    results = [
        SearchResult(title="a", url="https://x/1", domain="x",
                     image_url=f"{server}/blank.jpg"),
        SearchResult(title="b", url="https://x/2", domain="x"),
        SearchResult(title="c", url="https://x/3", domain="x",
                     image_url=f"{server}/same.png"),
    ]

    matching, _ = await matcher.match(input_embedding, results)

    # every candidate present, in search order, each with a decision and a reason
    assert matching.candidates_total == 3
    assert [c.position for c in matching.candidates] == [0, 1, 2]
    assert all(c.decision for c in matching.candidates)
    assert all(c.reason for c in matching.candidates)

    # digest reproducible from the recorded bundle
    recomputed = fingerprint_obj([c.model_dump() for c in matching.candidates])
    assert recomputed == matching.audit_bundle_sha256


@pytest.mark.asyncio
async def test_audit_bundle_digest_detects_reordering(
    server, images, input_embedding, matcher
):
    """Cherry-picking check: permuting the candidate list must change the digest."""
    _Handler.payloads = {"/same.png": (200, images["same_person"], "image/png")}
    results = [
        SearchResult(title="a", url="https://x/1", domain="x",
                     image_url=f"{server}/same.png"),
        SearchResult(title="b", url="https://x/2", domain="x"),
    ]
    matching, _ = await matcher.match(input_embedding, results)

    original = [c.model_dump() for c in matching.candidates]
    assert fingerprint_obj(original) == matching.audit_bundle_sha256

    reordered = [original[1], original[0]]
    assert fingerprint_obj(reordered) != matching.audit_bundle_sha256

    dropped = original[:1]
    assert fingerprint_obj(dropped) != matching.audit_bundle_sha256

    tweaked = [dict(original[0]), original[1]]
    tweaked[0]["similarity"] = (tweaked[0]["similarity"] or 0) + 0.000001
    assert fingerprint_obj(tweaked) != matching.audit_bundle_sha256
