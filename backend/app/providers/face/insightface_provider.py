"""InsightFace-based face detection and encoding provider."""

from __future__ import annotations

import threading

import numpy as np

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore

try:
    from insightface.app import FaceAnalysis  # type: ignore
except ImportError:
    FaceAnalysis = None  # type: ignore

from app.core.logging import get_logger
from app.core.exceptions import FaceDetectionError, FaceEncodingError

log = get_logger(__name__)

_app = None
_app_model_name: str | None = None

_app_lock = threading.Lock()

EMBEDDING_DIM = 512


def engine_name(model_name: str) -> str:
    """Identifier for the engine that produced a result, e.g. 'insightface:buffalo_l'."""
    return f"insightface:{model_name}"


def _get_insightface_app(model_name: str = "buffalo_l", det_thresh: float = 0.5):
    """Lazy-initialise the InsightFace analysis app (singleton)."""
    global _app, _app_model_name
    if _app is not None:
        return _app

    if FaceAnalysis is None:
        raise FaceDetectionError(
            "InsightFace is not installed. Install requirements.txt; no fallback detector exists."
        )

    with _app_lock:
        if _app is not None:
            return _app

        try:
            log.info("Initialising InsightFace model: %s", model_name)
            app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=0, det_thresh=det_thresh, det_size=(640, 640))
        except Exception as exc:
            log.error("Failed to initialise InsightFace model %r: %s", model_name, exc)
            raise FaceDetectionError(
                f"Face engine initialisation failed for model {model_name!r}: {exc}. "
                "The buffalo_l weights (~300MB) download to ~/.insightface/models on "
                "first use and require network access."
            ) from exc

        if "recognition" not in getattr(app, "models", {}):
            raise FaceDetectionError(
                f"Model {model_name!r} loaded without a recognition sub-model; "
                "it cannot produce face embeddings."
            )

        _app = app
        _app_model_name = model_name
        log.info("InsightFace model ready: %s", engine_name(model_name))
        return _app


def detect_faces(
    image_bytes: bytes,
    model_name: str = "buffalo_l",
    det_thresh: float = 0.5,
) -> list[dict]:
    """Detect faces and return one dict per face."""
    if cv2 is None or not hasattr(cv2, "imdecode"):
        raise FaceDetectionError("OpenCV is not available; cannot decode the image.")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise FaceDetectionError("Failed to decode image bytes.")

    app = _get_insightface_app(model_name, det_thresh)
    engine = engine_name(model_name)

    try:
        faces = app.get(img)
    except Exception as exc:
        log.error("InsightFace inference failed: %s", exc)
        raise FaceDetectionError(f"Face detection inference failed: {exc}") from exc

    results: list[dict] = []
    for index, face in enumerate(faces):
        embedding = getattr(face, "embedding", None)
        if embedding is None or getattr(embedding, "size", 0) != EMBEDDING_DIM:
            raise FaceDetectionError(
                f"{engine} returned a face without a valid {EMBEDDING_DIM}-d embedding."
            )

        det_score = float(face.det_score)
        bbox = np.asarray(face.bbox, dtype=float)
        kps = getattr(face, "kps", None)
        kps_list = np.asarray(kps, dtype=float).tolist() if kps is not None else []

        results.append({
            "face_index": index,
            "bbox": bbox.tolist(),
            "det_score": det_score,
            "confidence": det_score,
            "embedding": np.asarray(embedding, dtype=np.float32),
            "engine": engine,
            "kps": kps_list,
            "area_px": float(max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])),
            "blur_var": _blur_variance(img, bbox),
            **_pose_ratios(kps_list),
        })

    return results


def _blur_variance(img: np.ndarray, bbox: np.ndarray) -> float:
    """Variance of the Laplacian over the face crop — a standard sharpness proxy."""
    if cv2 is None or not hasattr(cv2, "Laplacian"):
        return 0.0
    h, w = img.shape[:2]
    x1 = max(0, int(bbox[0])); y1 = max(0, int(bbox[1]))
    x2 = min(w, int(bbox[2])); y2 = min(h, int(bbox[3]))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return 0.0
    crop = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _pose_ratios(kps: list) -> dict:
    """Crude yaw/pitch proxies from the 5 landmarks insightface already returns."""
    if not kps or len(kps) < 5:
        return {"yaw_ratio": 0.0, "pitch_ratio": 0.5}
    le, re, nose, lm, rm = kps[0], kps[1], kps[2], kps[3], kps[4]
    eye_mid_x = (le[0] + re[0]) / 2.0
    eye_mid_y = (le[1] + re[1]) / 2.0
    inter_ocular = float(np.hypot(re[0] - le[0], re[1] - le[1]))
    if inter_ocular < 1e-6:
        return {"yaw_ratio": 0.0, "pitch_ratio": 0.5}
    mouth_mid_y = (lm[1] + rm[1]) / 2.0
    vertical = mouth_mid_y - eye_mid_y
    yaw = (nose[0] - eye_mid_x) / inter_ocular
    pitch = (nose[1] - eye_mid_y) / vertical if abs(vertical) > 1e-6 else 0.5
    return {"yaw_ratio": float(yaw), "pitch_ratio": float(pitch)}


def l2_normalise(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v if n == 0.0 else (v / n).astype(np.float32)


def flip_average(emb_original: np.ndarray, emb_flipped: np.ndarray) -> np.ndarray:
    """Average an embedding with its horizontally-mirrored counterpart."""
    return l2_normalise(l2_normalise(emb_original) + l2_normalise(emb_flipped))


def detect_faces_flipped(
    image_bytes: bytes,
    model_name: str = "buffalo_l",
    det_thresh: float = 0.5,
) -> list[dict]:
    """Detect on the horizontally-mirrored image. Used for flip augmentation."""
    if cv2 is None:
        raise FaceDetectionError("OpenCV is not available.")
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise FaceDetectionError("Failed to decode image bytes.")
    ok, buf = cv2.imencode(".png", cv2.flip(img, 1))
    if not ok:
        raise FaceDetectionError("Failed to re-encode mirrored image.")
    return detect_faces(buf.tobytes(), model_name, det_thresh)


def encode_face(
    image_bytes: bytes,
    model_name: str = "buffalo_l",
    det_thresh: float = 0.5,
) -> np.ndarray:
    """Detect exactly one face and return its 512-d embedding."""
    faces = detect_faces(image_bytes, model_name, det_thresh)
    if len(faces) == 0:
        raise FaceEncodingError("No face found; cannot generate embedding.")
    if len(faces) > 1:
        faces.sort(key=lambda f: f["det_score"], reverse=True)
    return faces[0]["embedding"]
