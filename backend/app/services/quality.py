"""Face quality gating."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityThresholds:
    min_area_px: float = 40.0 * 40.0   # a 40x40 crop is the floor for buffalo_l
    min_blur_var: float = 12.0         # variance of Laplacian on the crop
    max_abs_yaw: float = 0.60          # nose offset / inter-ocular
    min_pitch: float = 0.10            # nose height between eye and mouth lines
    max_pitch: float = 0.95
    min_det_score: float = 0.55        # insightface's own detection confidence


DEFAULT_THRESHOLDS = QualityThresholds()


def quality_reason(face: dict, t: QualityThresholds = DEFAULT_THRESHOLDS) -> str:
    """Return "" if the face passes, else a short human-readable failure reason."""
    area = float(face.get("area_px", 0.0))
    if area < t.min_area_px:
        side = area ** 0.5
        return f"face too small ({side:.0f}px, min {t.min_area_px ** 0.5:.0f}px)"

    det = float(face.get("det_score", 0.0))
    if det < t.min_det_score:
        return f"detection confidence too low ({det:.3f} < {t.min_det_score:.2f})"

    blur = float(face.get("blur_var", 0.0))
    if blur < t.min_blur_var:
        return f"face too blurry (laplacian var {blur:.1f} < {t.min_blur_var:.1f})"

    yaw = abs(float(face.get("yaw_ratio", 0.0)))
    if yaw > t.max_abs_yaw:
        return f"head turned too far (yaw ratio {yaw:.2f} > {t.max_abs_yaw:.2f})"

    pitch = float(face.get("pitch_ratio", 0.5))
    if not (t.min_pitch <= pitch <= t.max_pitch):
        return (
            f"head tilted too far (pitch ratio {pitch:.2f} outside "
            f"[{t.min_pitch:.2f}, {t.max_pitch:.2f}])"
        )

    return ""


def passes(face: dict, t: QualityThresholds = DEFAULT_THRESHOLDS) -> bool:
    return quality_reason(face, t) == ""
