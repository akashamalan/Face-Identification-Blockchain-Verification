from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.providers.face.insightface_provider import detect_faces  # noqa: E402


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def embed(rgb_float: np.ndarray) -> np.ndarray | None:
    """Encode one LFW image -> 512-d embedding, or None if no face is detected.

    sklearn returns float32 RGB scaled to [0, 1], so it must be rescaled to [0, 255]
    before encoding — casting straight to uint8 collapses everything to black.
    LFW faces are ~150px in a 250x250 frame; we upscale 2x because the detector is
    configured for 640x640 inputs and small faces detect unreliably at native size.
    """
    import cv2

    rgb8 = np.clip(rgb_float * 255.0, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR)
    bgr = cv2.resize(bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        return None
    try:
        faces = detect_faces(buf.tobytes())
    except Exception:
        return None
    if not faces:
        return None
    return max(faces, key=lambda f: f["det_score"])["embedding"]


def percentile_report(name: str, xs: list[float]) -> dict:
    a = np.array(xs)
    return {
        "label": name,
        "n": int(a.size),
        "min": round(float(a.min()), 4),
        "p01": round(float(np.percentile(a, 1)), 4),
        "p05": round(float(np.percentile(a, 5)), 4),
        "p25": round(float(np.percentile(a, 25)), 4),
        "median": round(float(np.median(a)), 4),
        "p75": round(float(np.percentile(a, 75)), 4),
        "p95": round(float(np.percentile(a, 95)), 4),
        "p99": round(float(np.percentile(a, 99)), 4),
        "max": round(float(a.max()), 4),
        "mean": round(float(a.mean()), 4),
        "std": round(float(a.std()), 4),
    }


def histogram(same: list[float], diff: list[float], lo=-0.2, hi=1.0, bins=24) -> str:
    edges = np.linspace(lo, hi, bins + 1)
    hs, _ = np.histogram(same, bins=edges)
    hd, _ = np.histogram(diff, bins=edges)
    scale = max(hs.max(), hd.max()) or 1
    width = 40
    out = [f"{'range':>14}  {'same-person':<42} {'different-person'}"]
    for i in range(bins):
        s = "#" * int(round(hs[i] / scale * width))
        d = "#" * int(round(hd[i] / scale * width))
        out.append(f"[{edges[i]:+.2f},{edges[i+1]:+.2f})  {s:<42} {d}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=100,
                    help="target pairs PER CLASS (same / different)")
    args = ap.parse_args()

    from sklearn.datasets import fetch_lfw_pairs

    print("Fetching LFW pairs (color, full 250x250)...", flush=True)
    # slice_=None keeps the full 250x250 frame; the default slice_ crops to 125x94,
    # which is too small for reliable detection.
    ds = fetch_lfw_pairs(subset="train", color=True, resize=1.0, funneled=True, slice_=None)
    pairs, target = ds.pairs, ds.target  # (n,2,250,250,3), 1=same 0=different
    print(f"LFW train: {len(pairs)} pairs available", flush=True)

    same: list[float] = []
    diff: list[float] = []
    undetected = 0
    used = 0

    for idx in range(len(pairs)):
        if len(same) >= args.pairs and len(diff) >= args.pairs:
            break
        is_same = bool(target[idx] == 1)
        bucket = same if is_same else diff
        if len(bucket) >= args.pairs:
            continue

        e0 = embed(pairs[idx][0])
        e1 = embed(pairs[idx][1])
        used += 1
        if e0 is None or e1 is None:
            undetected += 1
            continue
        bucket.append(cosine(e0, e1))

        done = len(same) + len(diff)
        if done % 20 == 0:
            print(f"  ...{done} pairs scored ({len(same)} same / {len(diff)} diff)", flush=True)

    if not same or not diff:
        print("ERROR: could not build both classes", file=sys.stderr)
        return 1

    rs, rd = percentile_report("same-person", same), percentile_report("different-person", diff)

    # Sweep every candidate threshold; pick by Youden's J (maximises TPR-FPR), and
    # also report the strictest threshold that admits zero false accepts.
    grid = np.round(np.arange(0.10, 0.85, 0.005), 4)
    sweep = []
    for t in grid:
        tp = int(sum(1 for x in same if x >= t))
        fn = len(same) - tp
        fp = int(sum(1 for x in diff if x >= t))
        tn = len(diff) - fp
        tpr = tp / len(same)
        fpr = fp / len(diff)
        sweep.append({"t": float(t), "tp": tp, "fn": fn, "fp": fp, "tn": tn,
                      "tpr": round(tpr, 4), "fpr": round(fpr, 4),
                      "youden_j": round(tpr - fpr, 4)})

    best = max(sweep, key=lambda r: (r["youden_j"], -r["t"]))
    zero_fp = [r for r in sweep if r["fp"] == 0]
    strict = min(zero_fp, key=lambda r: r["t"]) if zero_fp else None

    gap_lo = round(max(d for d in diff), 4)   # worst different-person score
    gap_hi = round(min(s for s in same), 4)   # worst same-person score

    print("\n" + "=" * 78)
    print("SIMILARITY DISTRIBUTION (cosine, buffalo_l / w600k_r50)")
    print("=" * 78)
    for r in (rs, rd):
        print(f"\n{r['label']}  (n={r['n']})")
        print(f"  min {r['min']:+.4f}   p05 {r['p05']:+.4f}   p25 {r['p25']:+.4f}   "
              f"median {r['median']:+.4f}")
        print(f"  p75 {r['p75']:+.4f}   p95 {r['p95']:+.4f}   max {r['max']:+.4f}   "
              f"mean {r['mean']:+.4f} sd {r['std']:.4f}")

    print("\n" + histogram(same, diff))

    print("\n" + "=" * 78)
    print("SEPARATION")
    print("=" * 78)
    print(f"  highest different-person score : {gap_lo:+.4f}")
    print(f"  lowest  same-person score      : {gap_hi:+.4f}")
    print(f"  {'CLEAN GAP' if gap_hi > gap_lo else 'OVERLAP'}: "
          f"{'width ' + format(gap_hi - gap_lo, '+.4f') if gap_hi > gap_lo else 'distributions intersect'}")

    print(f"\n  Youden-optimal threshold : {best['t']:.3f}  "
          f"(TPR {best['tpr']:.3f}, FPR {best['fpr']:.3f}, "
          f"{best['fn']} missed / {best['fp']} false accepts)")
    if strict:
        print(f"  strictest zero-FP        : {strict['t']:.3f}  "
              f"(TPR {strict['tpr']:.3f}, {strict['fn']} missed, 0 false accepts)")
    print(f"\n  pairs scored: {used}   discarded (no face detected): {undetected}")

    out = {
        "model": "buffalo_l / w600k_r50",
        "metric": "cosine",
        "dataset": "LFW official train pairs (sklearn fetch_lfw_pairs, color, 250x250)",
        "same_person": rs,
        "different_person": rd,
        "highest_different": gap_lo,
        "lowest_same": gap_hi,
        "youden_optimal": best,
        "strictest_zero_fp": strict,
        "pairs_attempted": used,
        "pairs_discarded_no_face": undetected,
        "sweep": sweep,
    }
    dest = Path(__file__).resolve().parent.parent / "docs" / "threshold_calibration.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"\n  full sweep written to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
