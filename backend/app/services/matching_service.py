"""Stage 3 — candidate re-encoding and similarity scoring."""

from __future__ import annotations

import asyncio
import time

import httpx
import numpy as np

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.domain import CandidateEvidence, MatchingResult, SearchResult
from app.providers.face.insightface_provider import detect_faces
from app.utils.hashing import fingerprint_obj, sha256_hex

log = get_logger(__name__)

SIMILARITY_PRECISION = 6

DECISION_ACCEPTED = "accepted"
DECISION_REJECTED = "rejected_below_threshold"
DECISION_SKIPPED = "skipped"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two embeddings."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class MatchingService:
    def __init__(self, settings: Settings):
        self._threshold = settings.MATCH_THRESHOLD
        self._max_candidates = settings.MATCH_MAX_CANDIDATES
        self._concurrency = settings.MATCH_CONCURRENCY
        self._dl_concurrency = getattr(
            settings, 'MATCH_DOWNLOAD_CONCURRENCY', settings.MATCH_CONCURRENCY
        )
        self._timeout = settings.MATCH_DOWNLOAD_TIMEOUT_SECONDS
        self._max_bytes = settings.MATCH_MAX_IMAGE_BYTES
        self._model = settings.FACE_DETECTION_MODEL
        self._det_thresh = settings.FACE_DETECTION_THRESHOLD

    @property
    def threshold(self) -> float:
        return self._threshold

    async def match(
        self,
        input_embedding: np.ndarray,
        results: list[SearchResult],
    ) -> tuple[MatchingResult, SearchResult | None]:
        """Score candidates against the input face and pick the best confident match."""
        t0 = time.perf_counter()

        considered = results[: self._max_candidates]
        log.info(
            "Matching %d of %d candidates (threshold %.3f)",
            len(considered), len(results), self._threshold,
        )

        # downloads are I/O bound and want high concurrency; encoding is CPU
        # bound and contends with itself, so the two are gated separately.
        dl_sem = asyncio.Semaphore(self._dl_concurrency)
        cpu_sem = asyncio.Semaphore(self._concurrency)
        async with httpx.AsyncClient(
            timeout=self._timeout, follow_redirects=True
        ) as client:
            evidence = await asyncio.gather(*[
                self._evaluate(client, dl_sem, cpu_sem, position, result, input_embedding)
                for position, result in enumerate(considered)
            ])

        for position in range(len(considered), len(results)):
            r = results[position]
            r.similarity = None
            r.match_reason = f"not evaluated: beyond MATCH_MAX_CANDIDATES={self._max_candidates}"
            evidence.append(CandidateEvidence(
                position=position, url=r.url, domain=r.domain,
                decision=DECISION_SKIPPED, reason=r.match_reason,
            ))

        scored = [e for e in evidence if e.similarity is not None]
        best = max(scored, key=lambda e: e.similarity) if scored else None

        selected: SearchResult | None = None
        status = "no_confident_match"
        matched_sha = ""
        selected_position: int | None = None

        winner = best if (best is not None and best.similarity >= self._threshold) else None

        for e in scored:
            if e is winner:
                e.decision = DECISION_ACCEPTED
                e.reason = (
                    f"similarity {e.similarity:.4f} >= threshold {self._threshold:.3f}"
                )
            elif e.similarity < self._threshold:
                e.decision = DECISION_REJECTED
                e.reason = (
                    f"similarity {e.similarity:.4f} < threshold {self._threshold:.3f}"
                )
            else:
                e.decision = DECISION_REJECTED
                e.reason = (
                    f"similarity {e.similarity:.4f} clears threshold but is below "
                    f"best {best.similarity:.4f}"
                )
            results[e.position].match_reason = e.reason

        if winner is not None:
            selected = results[winner.position]
            selected_position = winner.position
            matched_sha = winner.image_sha256
            status = "match"

        ordered = sorted(evidence, key=lambda e: e.position)
        bundle_digest = fingerprint_obj([e.model_dump() for e in ordered])

        elapsed = (time.perf_counter() - t0) * 1000
        result = MatchingResult(
            status=status,
            threshold=self._threshold,
            candidates=ordered,
            selected_position=selected_position,
            best_similarity=best.similarity if best else None,
            matched_image_sha256=matched_sha,
            audit_bundle_sha256=bundle_digest,
            candidates_total=len(ordered),
            candidates_scored=len(scored),
            candidates_skipped=len(ordered) - len(scored),
            matching_time_ms=round(elapsed, 1),
        )

        log.info(
            "Matching %s: %d/%d scored, best=%s, threshold=%.3f, bundle=%s… (%.0fms)",
            status, len(scored), len(ordered),
            f"{best.similarity:.4f}" if best else "none",
            self._threshold, bundle_digest[:16], elapsed,
        )
        return result, selected


    async def _evaluate(
        self,
        client: httpx.AsyncClient,
        dl_sem: asyncio.Semaphore,
        cpu_sem: asyncio.Semaphore,
        position: int,
        result: SearchResult,
        input_embedding: np.ndarray,
    ) -> CandidateEvidence:
        ev = CandidateEvidence(
            position=position, url=result.url, domain=result.domain,
            decision=DECISION_SKIPPED,
        )

        sources = self._image_sources(result)
        if not sources:
            ev.reason = "no image_url or thumbnail on this result"
            result.similarity = None
            result.match_reason = ev.reason
            return ev

        faces: list[dict] = []
        failures: list[str] = []

        for source_field, image_url in sources:
            t_dl = time.perf_counter()
            async with dl_sem:
                data, download_error = await self._download(client, image_url)
            ev.download_ms = round((time.perf_counter() - t_dl) * 1000, 1)
            if download_error:
                failures.append(f"{source_field}: {download_error}")
                continue

            ev.image_source = source_field
            ev.image_bytes = len(data)
            ev.image_sha256 = sha256_hex(data)

            t_enc = time.perf_counter()
            async with cpu_sem:
                found, encode_error = await asyncio.to_thread(self._encode, data)
            ev.encode_ms = round((time.perf_counter() - t_enc) * 1000, 1)
            if encode_error:
                failures.append(f"{source_field}: {encode_error}")
                continue

            faces = found
            break

        if not faces:
            ev.reason = "; ".join(failures) or "no usable image"
            result.similarity = None
            result.match_reason = ev.reason
            return ev

        ev.faces_detected = len(faces)

        scored = [
            (cosine_similarity(input_embedding, f["embedding"]), f) for f in faces
        ]
        best_sim, best_face = max(scored, key=lambda pair: pair[0])

        ev.similarity = round(best_sim, SIMILARITY_PRECISION)
        ev.matched_face_index = int(best_face.get("face_index", 0))
        ev.matched_face_bbox = [round(v, 2) for v in best_face.get("bbox", [])]
        ev.matched_face_det_score = round(float(best_face.get("det_score", 0.0)), 4)
        ev.reason = (
            f"scored against {len(faces)} face(s) from {source_field}; "
            f"best is face #{ev.matched_face_index}"
        )
        result.similarity = ev.similarity
        return ev

    def _image_sources(self, result: SearchResult) -> list[tuple[str, str]]:
        """Every candidate image URL, best first, de-duplicated."""
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for field, url in (("image_url", result.image_url), ("thumbnail", result.thumbnail)):
            if not url or url in seen or url == result.url:
                continue
            seen.add(url)
            out.append((field, url))
        return out

    async def _download(
        self, client: httpx.AsyncClient, url: str
    ) -> tuple[bytes, str]:
        """Fetch an image, capping size by streaming. Returns (bytes, error_reason)."""
        try:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    return b"", f"download failed: HTTP {response.status_code}"

                ctype = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if ctype and not ctype.startswith("image/"):
                    return b"", f"not an image (content-type {ctype or 'unknown'})"

                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > self._max_bytes:
                    return b"", (
                        f"image too large: content-length {declared} bytes "
                        f"> cap {self._max_bytes}"
                    )

                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > self._max_bytes:
                        return b"", (
                            f"image too large: exceeded cap {self._max_bytes} bytes "
                            "mid-download"
                        )
                    chunks.append(chunk)

        except httpx.TimeoutException:
            return b"", f"download timed out after {self._timeout}s"
        except httpx.RequestError as exc:
            return b"", f"download failed: {type(exc).__name__}"
        except Exception as exc:  # unexpected, but must not abort the whole stage
            return b"", f"download failed: {type(exc).__name__}"

        if total == 0:
            return b"", "download returned an empty body"
        return b"".join(chunks), ""

    def _encode(self, data: bytes) -> tuple[list[dict], str]:
        """Detect+encode faces in downloaded bytes. Returns (faces, error_reason)."""
        try:
            faces = detect_faces(data, self._model, self._det_thresh)
        except Exception as exc:
            # Record the MESSAGE, not just the class name. Logging only
            detail = str(exc).strip() or type(exc).__name__
            return [], f"could not encode: {detail}"
        if not faces:
            return [], "no face detected in candidate image"
        return faces, ""
