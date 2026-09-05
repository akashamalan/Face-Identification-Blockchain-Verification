"""Measure matching accuracy variants on the SAME LFW pairs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.providers.face.insightface_provider import (  # noqa: E402
    detect_faces, flip_average, l2_normalise,
)
from app.services.quality import QualityThresholds, quality_reason  # noqa: E402

CACHE = ROOT / "docs" / "lfw_embeddings.npz"


def to_png_bytes(rgb_float: np.ndarray, upscale: float = 2.0) -> bytes:
    import cv2
    rgb8 = np.clip(rgb_float * 255.0, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR)
    if upscale != 1.0:
        bgr = cv2.resize(bgr, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    return cv2.imencode(".png", bgr)[1].tobytes()


def mirror_png(png: bytes) -> bytes:
    import cv2
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    return cv2.imencode(".png", cv2.flip(img, 1))[1].tobytes()


def best_face(png: bytes):
    try:
        faces = detect_faces(png)
    except Exception:
        return None
    if not faces:
        return None
    return max(faces, key=lambda f: f["det_score"])


def encode_all(n_per_class: int):
    from sklearn.datasets import fetch_lfw_pairs

    print("Fetching LFW pairs...", flush=True)
    ds = fetch_lfw_pairs(subset="train", color=True, resize=1.0, funneled=True, slice_=None)
    pairs, target = ds.pairs, ds.target

    rows = []          # one per pair
    same_n = diff_n = 0

    for idx in range(len(pairs)):
        if same_n >= n_per_class and diff_n >= n_per_class:
            break
        is_same = bool(target[idx] == 1)
        if is_same and same_n >= n_per_class:
            continue
        if not is_same and diff_n >= n_per_class:
            continue

        rec = {"same": is_same}
        ok = True
        for side in (0, 1):
            png = to_png_bytes(pairs[idx][side])
            f = best_face(png)
            if f is None:
                ok = False
                break
            fm = best_face(mirror_png(png))
            rec[f"e{side}"] = f["embedding"]
            rec[f"m{side}"] = fm["embedding"] if fm is not None else f["embedding"]
            rec[f"det{side}"] = f["det_score"]
            rec[f"area{side}"] = f["area_px"]
            rec[f"blur{side}"] = f["blur_var"]
            rec[f"yaw{side}"] = f["yaw_ratio"]
            rec[f"pitch{side}"] = f["pitch_ratio"]
        if not ok:
            continue

        rows.append(rec)
        if is_same:
            same_n += 1
        else:
            diff_n += 1
        if len(rows) % 20 == 0:
            print(f"  ...{len(rows)} pairs encoded ({same_n} same / {diff_n} diff)", flush=True)

    print(f"encoded {len(rows)} pairs", flush=True)
    arr = {"same": np.array([r["same"] for r in rows], dtype=bool)}
    for k in ("e0", "e1", "m0", "m1"):
        arr[k] = np.stack([r[k] for r in rows])
    for k in ("det0", "det1", "area0", "area1", "blur0", "blur1",
              "yaw0", "yaw1", "pitch0", "pitch1"):
        arr[k] = np.array([r[k] for r in rows], dtype=float)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, **arr)
    print(f"cached -> {CACHE}", flush=True)
    return arr


def cos(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    an = a / np.linalg.norm(a, axis=1, keepdims=True)
    bn = b / np.linalg.norm(b, axis=1, keepdims=True)
    return np.sum(an * bn, axis=1)


def face_dict(d, side, i):
    return {
        "det_score": d[f"det{side}"][i], "area_px": d[f"area{side}"][i],
        "blur_var": d[f"blur{side}"][i], "yaw_ratio": d[f"yaw{side}"][i],
        "pitch_ratio": d[f"pitch{side}"][i],
    }


def stats(x: np.ndarray) -> dict:
    return {
        "n": int(x.size), "min": round(float(x.min()), 4),
        "p05": round(float(np.percentile(x, 5)), 4),
        "median": round(float(np.median(x)), 4),
        "p95": round(float(np.percentile(x, 95)), 4),
        "max": round(float(x.max()), 4),
        "mean": round(float(x.mean()), 4), "std": round(float(x.std()), 4),
    }


def sweep(same: np.ndarray, diff: np.ndarray):
    grid = np.round(np.arange(0.05, 0.90, 0.005), 4)
    out = []
    for t in grid:
        tp = int((same >= t).sum()); fp = int((diff >= t).sum())
        tpr = tp / len(same); fpr = fp / len(diff)
        out.append({"t": float(t), "tpr": round(tpr, 4), "fpr": round(fpr, 4),
                    "fn": len(same) - tp, "fp": fp, "j": round(tpr - fpr, 4)})
    return out


def evaluate(name: str, same: np.ndarray, diff: np.ndarray, gated: int = 0):
    sw = sweep(same, diff)
    zero_fp = [r for r in sw if r["fp"] == 0]
    best_tpr = max((r["tpr"] for r in zero_fp), default=0.0)
    plateau = [r for r in zero_fp if r["tpr"] == best_tpr]
    top = max(plateau, key=lambda r: r["t"]) if plateau else None
    return {
        "variant": name,
        "pairs_used": {"same": int(same.size), "diff": int(diff.size)},
        "gated_out": gated,
        "same": stats(same), "diff": stats(diff),
        "highest_diff": round(float(diff.max()), 4),
        "lowest_same": round(float(same.min()), 4),
        "gap": round(float(same.min() - diff.max()), 4),
        "tpr_at_zero_fpr": round(best_tpr, 4),
        "plateau_lo": plateau[0]["t"] if plateau else None,
        "plateau_hi": top["t"] if top else None,
        "sweep": sw,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=100)
    ap.add_argument("--reuse", action="store_true", help="use cached embeddings")
    args = ap.parse_args()

    if args.reuse and CACHE.exists():
        print(f"reusing {CACHE}")
        d = dict(np.load(CACHE))
    else:
        d = encode_all(args.pairs)

    same_mask = d["same"]
    e0, e1, m0, m1 = d["e0"], d["e1"], d["m0"], d["m1"]

    base = cos(e0, e1)

    q_flip = np.stack([flip_average(e0[i], m0[i]) for i in range(len(e0))])
    flip = cos(q_flip, e1)

    results = [
        evaluate("baseline", base[same_mask], base[~same_mask]),
        evaluate("flip", flip[same_mask], flip[~same_mask]),
    ]

    t = QualityThresholds()
    keep = np.array([
        quality_reason(face_dict(d, 0, i), t) == ""
        and quality_reason(face_dict(d, 1, i), t) == ""
        for i in range(len(e0))
    ])
    gated = int((~keep).sum())
    if keep.sum() > 10:
        fq = flip[keep]; sm = same_mask[keep]
        if sm.sum() > 3 and (~sm).sum() > 3:
            results.append(evaluate("flip+quality", fq[sm], fq[~sm], gated=gated))

    print("\n" + "=" * 92)
    print("VARIANT COMPARISON — same 100+100 LFW pairs, buffalo_l, cosine")
    print("=" * 92)
    hdr = f"{'variant':<16}{'same med':>10}{'same p05':>10}{'diff max':>10}{'gap':>9}{'TPR@0FPR':>11}{'plateau':>16}{'gated':>7}"
    print(hdr)
    print("-" * 92)
    for r in results:
        pl = f"{r['plateau_lo']:.3f}–{r['plateau_hi']:.3f}" if r["plateau_hi"] else "n/a"
        print(f"{r['variant']:<16}{r['same']['median']:>10.4f}{r['same']['p05']:>10.4f}"
              f"{r['highest_diff']:>10.4f}{r['gap']:>9.4f}{r['tpr_at_zero_fpr']:>11.4f}"
              f"{pl:>16}{r['gated_out']:>7}")

    print("\nVERDICT")
    b = results[0]
    for r in results[1:]:
        d_tpr = r["tpr_at_zero_fpr"] - b["tpr_at_zero_fpr"]
        d_gap = r["gap"] - b["gap"]
        keep_it = d_tpr > 0 or (d_tpr == 0 and d_gap > 0)
        print(f"  {r['variant']:<14} ΔTPR@0FPR {d_tpr:+.4f}   Δgap {d_gap:+.4f}   "
              f"-> {'KEEP' if keep_it else 'REVERT'}")

    dest = ROOT / "docs" / "variant_measurement.json"
    dest.write_text(json.dumps(results, indent=2))
    print(f"\nwritten -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
