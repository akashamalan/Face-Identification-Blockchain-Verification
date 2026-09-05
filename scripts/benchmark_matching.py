"""Measure matching-accuracy changes on the SAME LFW pairs, before and after.

Design: extract per-image features ONCE (normal embedding, mirrored embedding,
det_score, box area, blur variance, yaw/pitch) and cache them. Every variant is
then evaluated from that cache with no further model calls, so adding a variant
costs nothing and each is measured on identical data.

Variants are compared on: same/different distributions, the class gap, and TPR at
FPR = 0 (the operating point that matters — a false accept means naming the wrong
person).

Usage:
    backend/venv/Scripts/python.exe scripts/benchmark_matching.py --pairs 100
    backend/venv/Scripts/python.exe scripts/benchmark_matching.py --pairs 100 --reuse
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.providers.face.insightface_provider import (  # noqa: E402
    detect_faces,
    flip_average,
    l2_normalise,
)

CACHE = ROOT / "docs" / "benchmark_features.npz"


# ── feature extraction ──────────────────────────────────────────────────────

def _to_png(rgb_float: np.ndarray) -> bytes:
    """LFW arrives as float32 RGB in [0,1]; rescale, BGR, upscale 2x, encode."""
    import cv2

    rgb8 = np.clip(rgb_float * 255.0, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR)
    bgr = cv2.resize(bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    return cv2.imencode(".png", bgr)[1].tobytes()


def _features(rgb_float: np.ndarray) -> dict | None:
    """Normal + mirrored embedding and quality metrics for the best face."""
    import cv2

    png = _to_png(rgb_float)
    try:
        faces = detect_faces(png)
    except Exception:
        return None
    if not faces:
        return None
    f = max(faces, key=lambda x: x["det_score"])

    # mirrored pass — detect on the flipped image so alignment is done natively
    rgb8 = np.clip(rgb_float * 255.0, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR)
    bgr = cv2.resize(bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    png_f = cv2.imencode(".png", cv2.flip(bgr, 1))[1].tobytes()
    try:
        faces_f = detect_faces(png_f)
        emb_f = (
            max(faces_f, key=lambda x: x["det_score"])["embedding"]
            if faces_f
            else f["embedding"]
        )
    except Exception:
        emb_f = f["embedding"]

    return {
        "emb": f["embedding"],
        "emb_flip": emb_f,
        "det": f["det_score"],
        "area": f["area_px"],
        "blur": f["blur_var"],
        "yaw": f["yaw_ratio"],
        "pitch": f["pitch_ratio"],
    }


def extract(n_per_class: int) -> dict:
    from sklearn.datasets import fetch_lfw_pairs

    print("Fetching LFW pairs...", flush=True)
    ds = fetch_lfw_pairs(
        subset="train", color=True, resize=1.0, funneled=True, slice_=None
    )
    pairs, target = ds.pairs, ds.target

    A_emb, A_flip, B_emb, B_flip, labels = [], [], [], [], []
    A_q, B_q = [], []
    same = diff = skipped = 0

    for idx in range(len(pairs)):
        if same >= n_per_class and diff >= n_per_class:
            break
        is_same = bool(target[idx] == 1)
        if (is_same and same >= n_per_class) or (not is_same and diff >= n_per_class):
            continue

        fa = _features(pairs[idx][0])
        fb = _features(pairs[idx][1])
        if fa is None or fb is None:
            skipped += 1
            continue

        A_emb.append(fa["emb"]); A_flip.append(fa["emb_flip"])
        B_emb.append(fb["emb"]); B_flip.append(fb["emb_flip"])
        A_q.append([fa["det"], fa["area"], fa["blur"], fa["yaw"], fa["pitch"]])
        B_q.append([fb["det"], fb["area"], fb["blur"], fb["yaw"], fb["pitch"]])
        labels.append(1 if is_same else 0)
        if is_same:
            same += 1
        else:
            diff += 1

        done = same + diff
        if done % 20 == 0:
            print(f"  ...{done} pairs ({same} same / {diff} diff)", flush=True)

    data = {
        "A_emb": np.array(A_emb, dtype=np.float32),
        "A_flip": np.array(A_flip, dtype=np.float32),
        "B_emb": np.array(B_emb, dtype=np.float32),
        "B_flip": np.array(B_flip, dtype=np.float32),
        "A_q": np.array(A_q, dtype=np.float32),
        "B_q": np.array(B_q, dtype=np.float32),
        "labels": np.array(labels, dtype=np.int32),
    }
    np.savez_compressed(CACHE, **data)
    print(f"\ncached {len(labels)} pairs -> {CACHE}  (skipped {skipped})")
    return data


# ── evaluation ──────────────────────────────────────────────────────────────

def cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def sweep(same: list[float], diff: list[float]) -> dict:
    """TPR at FPR=0 is the headline: the strictest threshold with no false accepts."""
    grid = np.round(np.arange(0.05, 0.90, 0.005), 4)
    rows = []
    for t in grid:
        tp = sum(1 for x in same if x >= t)
        fp = sum(1 for x in diff if x >= t)
        rows.append({
            "t": float(t),
            "tpr": tp / len(same) if same else 0.0,
            "fpr": fp / len(diff) if diff else 0.0,
            "fn": len(same) - tp,
            "fp": fp,
        })
    zero_fp = [r for r in rows if r["fp"] == 0]
    best_zero = max(zero_fp, key=lambda r: r["tpr"]) if zero_fp else None
    plateau = [r for r in zero_fp if best_zero and r["tpr"] == best_zero["tpr"]]
    return {
        "rows": rows,
        "tpr_at_fpr0": best_zero["tpr"] if best_zero else 0.0,
        "plateau_lo": min(p["t"] for p in plateau) if plateau else None,
        "plateau_hi": max(p["t"] for p in plateau) if plateau else None,
    }


def stats(xs: list[float]) -> dict:
    a = np.array(xs)
    return {
        "n": int(a.size),
        "min": float(a.min()), "p05": float(np.percentile(a, 5)),
        "median": float(np.median(a)), "p95": float(np.percentile(a, 95)),
        "max": float(a.max()), "mean": float(a.mean()), "std": float(a.std()),
    }


def evaluate(name: str, d: dict, use_flip: bool, gate: dict | None) -> dict:
    """Score every pair under one variant. Query side = A (flip-augmented in
    production); candidate side = B (single pass, as in the real pipeline)."""
    same, diff = [], []
    gated_same = gated_diff = 0

    for i in range(len(d["labels"])):
        qa, qb = d["A_q"][i], d["B_q"][i]
        if gate:
            def fails(q):
                det, area, blur, yaw, pitch = q
                return (
                    det < gate["det"]
                    or area < gate["area"]
                    or blur < gate["blur"]
                    or abs(yaw) > gate["yaw"]
                    or abs(pitch - 0.5) > gate["pitch"]
                )
            if fails(qa) or fails(qb):
                if d["labels"][i] == 1:
                    gated_same += 1
                else:
                    gated_diff += 1
                continue

        q = (
            flip_average(d["A_emb"][i], d["A_flip"][i])
            if use_flip
            else l2_normalise(d["A_emb"][i])
        )
        c = l2_normalise(d["B_emb"][i])
        s = cos(q, c)
        (same if d["labels"][i] == 1 else diff).append(s)

    if not same or not diff:
        return {"variant": name, "error": "a class was emptied by the gate"}

    sw = sweep(same, diff)
    return {
        "variant": name,
        "same": stats(same),
        "diff": stats(diff),
        "gap": float(min(same) - max(diff)),
        "highest_diff": float(max(diff)),
        "lowest_same": float(min(same)),
        "tpr_at_fpr0": sw["tpr_at_fpr0"],
        "plateau_lo": sw["plateau_lo"],
        "plateau_hi": sw["plateau_hi"],
        "gated_out": {"same": gated_same, "diff": gated_diff},
    }


def show(r: dict) -> None:
    if "error" in r:
        print(f"\n{r['variant']:<34} ERROR: {r['error']}")
        return
    print(f"\n{r['variant']}")
    print(f"  same  n={r['same']['n']:<4} median {r['same']['median']:+.4f}  "
          f"p05 {r['same']['p05']:+.4f}  min {r['same']['min']:+.4f}")
    print(f"  diff  n={r['diff']['n']:<4} median {r['diff']['median']:+.4f}  "
          f"p95 {r['diff']['p95']:+.4f}  max {r['diff']['max']:+.4f}")
    print(f"  gap (lowest_same - highest_diff) : {r['gap']:+.4f}")
    print(f"  TPR @ FPR=0                      : {r['tpr_at_fpr0']:.4f}"
          f"   plateau [{r['plateau_lo']}, {r['plateau_hi']}]")
    if r["gated_out"]["same"] or r["gated_out"]["diff"]:
        print(f"  gated out: {r['gated_out']['same']} same, {r['gated_out']['diff']} diff")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=100)
    ap.add_argument("--reuse", action="store_true", help="use the cached features")
    args = ap.parse_args()

    if args.reuse and CACHE.exists():
        z = np.load(CACHE)
        d = {k: z[k] for k in z.files}
        print(f"reusing cached features: {len(d['labels'])} pairs")
    else:
        d = extract(args.pairs)

    # Gate thresholds. area is in the 2x-upscaled frame, so 40x40 in the original
    # is 80x80 = 6400px here.
    # Thresholds set FROM the observed distribution, not guessed. Across 400 LFW
    # faces: det p01=0.724 min=0.607; area min=24604; blur p01=6.28 min=4.40;
    # |yaw| p99~0.29 max=1.00; |pitch-0.5| p95~0.19 max=0.38.
    # A gate should reject outliers, not the median — the first pass used
    # blur>=25 (above LFW's median of 15.3) and threw away 84% of the data.
    GATE = {"det": 0.50, "area": 6400.0, "blur": 5.0, "yaw": 0.60, "pitch": 0.40}

    results = [
        evaluate("1. baseline (no flip, no gate)", d, use_flip=False, gate=None),
        evaluate("2. + flip augmentation (query)", d, use_flip=True, gate=None),
        evaluate("3. + flip + quality gate", d, use_flip=True, gate=GATE),
        evaluate("4. gate only (no flip)", d, use_flip=False, gate=GATE),
    ]

    print("\n" + "=" * 78)
    print("VARIANT COMPARISON — identical pairs, identical features")
    print("=" * 78)
    for r in results:
        show(r)

    base = results[0]
    print("\n" + "=" * 78)
    print("DELTA vs baseline")
    print("=" * 78)
    print(f"{'variant':<34} {'gap':>10} {'Δgap':>9} {'TPR@FPR0':>10} {'Δ':>8}")
    for r in results:
        if "error" in r:
            continue
        print(f"{r['variant']:<34} {r['gap']:>+10.4f} "
              f"{r['gap'] - base['gap']:>+9.4f} "
              f"{r['tpr_at_fpr0']:>10.4f} "
              f"{r['tpr_at_fpr0'] - base['tpr_at_fpr0']:>+8.4f}")

    out = ROOT / "docs" / "benchmark_results.json"
    out.write_text(json.dumps({"gate": GATE, "results": results}, indent=2))
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
