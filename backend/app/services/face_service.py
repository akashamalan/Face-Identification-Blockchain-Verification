"""Face detection and encoding service — business logic layer.

InsightFace inference is synchronous, CPU-bound, and slow (~5s on the first call
including model load, a few hundred ms after). Calling it directly from an async
route blocks the event loop for that entire duration, serialising every other
request in the process. The public API here is therefore async and pushes the
blocking work to a worker thread via asyncio.to_thread; the `_sync` variants remain
available for synchronous callers such as tests and scripts.
"""

from __future__ import annotations

import asyncio
import time
from typing import NamedTuple

import numpy as np

from app.core.config import Settings
from app.core.exceptions import (
    FaceDetectionError,
    NoFaceDetectedError,
    MultipleFacesError,
)
from app.core.logging import get_logger
from app.models.domain import FaceData
from app.providers.face.insightface_provider import detect_faces

log = get_logger(__name__)


class FaceDetection(NamedTuple):
    """Detection metadata plus the raw embedding.

    `data` is the API-safe part. `embedding` stays server-side — it is passed to
    MatchingService for similarity scoring and is never returned to a client.
    """
    data: FaceData
    embedding: np.ndarray


class FaceService:
    def __init__(self, settings: Settings):
        self._model = settings.FACE_DETECTION_MODEL
        self._threshold = settings.FACE_DETECTION_THRESHOLD

    async def detect(
        self, image_bytes: bytes, allow_multiple: bool = False
    ) -> FaceDetection:
        """Detect faces off the event loop. Rejects zero or multiple faces by default.

        Returns the embedding alongside the metadata. It used to be computed and then
        dropped on the floor here, which is why stage 3 had nothing to compare against.
        The embedding is never serialised into an API response — FaceDetection.data is
        the only part that reaches the client.
        """
        return await asyncio.to_thread(self.detect_sync, image_bytes, allow_multiple)

    async def detect_and_encode(self, image_bytes: bytes) -> tuple[FaceData, list[float]]:
        """Detect one face off the event loop and return (metadata, embedding)."""
        return await asyncio.to_thread(self.detect_and_encode_sync, image_bytes)

    def detect_sync(
        self, image_bytes: bytes, allow_multiple: bool = False
    ) -> FaceDetection:
        """Blocking detect. Prefer `detect()` from async code."""
        t0 = time.perf_counter()

        try:
            faces = detect_faces(image_bytes, self._model, self._threshold)
        except FaceDetectionError:
            raise
        except Exception as exc:
            log.error("Unexpected face detection error: %s", exc)
            raise FaceDetectionError(f"Face detection error: {exc}") from exc

        elapsed = (time.perf_counter() - t0) * 1000
        count = len(faces)

        if count == 0:
            raise NoFaceDetectedError()

        if count > 1 and not allow_multiple:
            raise MultipleFacesError(count)

        best = max(faces, key=lambda f: f["det_score"])

        log.info(
            "Face detected: engine=%s count=%d det_score=%.3f time=%.0fms",
            best["engine"], count, best["det_score"], elapsed,
        )

        return FaceDetection(
            data=FaceData(
                face_detected=True,
                face_count=count,
                embedding_generated=True,
                bbox=best["bbox"],
                confidence=best["det_score"],
                det_score=best["det_score"],
                engine=best["engine"],
                processing_time_ms=round(elapsed, 1),
            ),
            embedding=best["embedding"],
        )

    def detect_and_encode_sync(self, image_bytes: bytes) -> tuple[FaceData, list[float]]:
        """Blocking detect+encode. Prefer `detect_and_encode()` from async code.

        The embedding is kept as a Python list and never logged or sent to the frontend.
        """
        t0 = time.perf_counter()

        try:
            faces = detect_faces(image_bytes, self._model, self._threshold)
        except FaceDetectionError:
            raise
        except Exception as exc:
            raise FaceDetectionError(f"Face detection error: {exc}") from exc

        elapsed = (time.perf_counter() - t0) * 1000
        count = len(faces)

        if count == 0:
            raise NoFaceDetectedError()
        if count > 1:
            raise MultipleFacesError(count)

        face = faces[0]
        embedding = face["embedding"].tolist()

        data = FaceData(
            face_detected=True,
            face_count=1,
            embedding_generated=True,
            bbox=face["bbox"],
            confidence=face["det_score"],
            det_score=face["det_score"],
            engine=face["engine"],
            processing_time_ms=round(elapsed, 1),
        )
        return data, embedding
