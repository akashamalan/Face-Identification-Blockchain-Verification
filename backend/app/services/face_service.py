"""Face detection and encoding service — business logic layer."""

from __future__ import annotations

import time

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


class FaceService:
    def __init__(self, settings: Settings):
        self._model = settings.FACE_DETECTION_MODEL
        self._threshold = settings.FACE_DETECTION_THRESHOLD

    def detect(self, image_bytes: bytes, allow_multiple: bool = False) -> FaceData:
        """Detect faces and return metadata. Rejects zero or multiple faces by default."""
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

        best = max(faces, key=lambda f: f["confidence"])

        log.info("Face detected: count=%d confidence=%.3f time=%.0fms", count, best["confidence"], elapsed)

        return FaceData(
            face_detected=True,
            face_count=count,
            embedding_generated=True,
            bbox=best["bbox"],
            confidence=best["confidence"],
            processing_time_ms=round(elapsed, 1),
        )

    def detect_and_encode(self, image_bytes: bytes) -> tuple[FaceData, list[float]]:
        """Detect one face and return (metadata, embedding as list of floats).

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
            confidence=face["confidence"],
            processing_time_ms=round(elapsed, 1),
        )
        return data, embedding
