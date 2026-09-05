"""Per-stage latency profiler.

Measures each pipeline stage independently with perf_counter and reports
mean/median/p95/p99. Costs nothing to run: face work is local, candidate images
are served from an in-process HTTP server, and the chain stages use the in-memory
provider. No SerpAPI calls, no gas.

    backend/venv/Scripts/python.exe scripts/profile_pipeline.py
    backend/venv/Scripts/python.exe scripts/profile_pipeline.py --concurrency-sweep
"""

from __future__ import annotations

import argparse
import asyncio
import http.server
import statistics as st
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings                      # noqa: E402
from app.models.domain import SearchResult                    # noqa: E402
from app.providers.blockchain.local_provider import LocalBlockchainProvider  # noqa: E402
from app.services.blockchain_service import BlockchainService  # noqa: E402
from app.services.face_service import FaceService             # noqa: E402
from app.services.fingerprint_service import FingerprintService  # noqa: E402
from app.services.matching_service import MatchingService     # noqa: E402
from app.services.verification_service import VerificationService  # noqa: E402

SAMPLE = ROOT / "sample_data" / "demo_face.jpg"


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1))))
    return s[k]


def report(name: str, xs: list[float], unit: str = "ms") -> dict:
    row = {
        "stage": name,
        "n": len(xs),
        "mean": st.mean(xs) if xs else 0.0,
        "median": st.median(xs) if xs else 0.0,
        "p95": pct(xs, 95),
        "p99": pct(xs, 99),
        "min": min(xs) if xs else 0.0,
        "max": max(xs) if xs else 0.0,
    }
    print(
        f"  {name:<34} n={row['n']:<3} "
        f"mean {row['mean']:8.1f}  med {row['median']:8.1f}  "
        f"p95 {row['p95']:8.1f}  p99 {row['p99']:8.1f}  {unit}"
    )
    return row


class _Server:
    """Serves candidate images locally so download cost is measured without WAN noise."""

    def __init__(self, payloads: dict[str, bytes]):
        handler_payloads = payloads

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = handler_payloads.get(self.path)
                if body is None:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"x")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self._srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self._srv.server_address[1]}"

    def stop(self):
        self._srv.shutdown()


def build_candidates(n: int) -> tuple[dict[str, bytes], list[str]]:
    """n distinct face images, so no cache or dedup can shortcut the work."""
    img = cv2.imdecode(np.frombuffer(SAMPLE.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    payloads, paths = {}, []
    for i in range(n):
        v = cv2.convertScaleAbs(img, alpha=1.0 + (i % 7) * 0.03, beta=(i % 5) * 4)
        if i % 3 == 1:
            v = cv2.resize(v, None, fx=0.9, fy=0.9)
        path = f"/c{i}.jpg"
        payloads[path] = cv2.imencode(".jpg", v)[1].tobytes()
        paths.append(path)
    return payloads, paths


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=8)
    ap.add_argument("--candidates", type=int, default=12)
    ap.add_argument("--concurrency-sweep", action="store_true")
    args = ap.parse_args()

    settings = get_settings()
    face = FaceService(settings)
    img_bytes = SAMPLE.read_bytes()

    print("=" * 92)
    print("PER-STAGE LATENCY  (local only: no SerpAPI, no chain gas)")
    print("=" * 92)

    # warm the model so the one-off load is not charged to the first sample
    face.detect_sync(img_bytes)

    rows = []

    # ── stage 1: face detection ────────────────────────────────────────────
    xs = []
    for _ in range(args.runs):
        t = time.perf_counter()
        det = face.detect_sync(img_bytes)
        xs.append((time.perf_counter() - t) * 1000)
    rows.append(report("1 face detection (1 image)", xs))
    embedding = det.embedding

    # ── stage 2 component: encode ONE candidate ────────────────────────────
    payloads, paths = build_candidates(args.candidates)
    srv = _Server(payloads)
    try:
        from app.providers.face.insightface_provider import detect_faces

        one = payloads[paths[0]]
        xs = []
        for _ in range(args.runs):
            t = time.perf_counter()
            detect_faces(one, settings.FACE_DETECTION_MODEL, settings.FACE_DETECTION_THRESHOLD)
            xs.append((time.perf_counter() - t) * 1000)
        rows.append(report("2a per-candidate encode", xs))
        per_candidate = st.median(xs)

        # ── stage 2: full matching over N candidates ───────────────────────
        matcher = MatchingService(settings)
        results = [
            SearchResult(title=f"c{i}", url=f"https://x/{i}", domain="x",
                         image_url=f"{srv.base}{p}")
            for i, p in enumerate(paths)
        ]
        xs = []
        for _ in range(3):
            fresh = [r.model_copy(deep=True) for r in results]
            t = time.perf_counter()
            m, _sel = await matcher.match(embedding, fresh)
            xs.append((time.perf_counter() - t) * 1000)
        rows.append(report(f"2b matching ({args.candidates} candidates)", xs))
        matching_median = st.median(xs)
        print(f"     -> scored {m.candidates_scored}/{m.candidates_total}, "
              f"concurrency={settings.MATCH_CONCURRENCY}")

        # ── stage 3: fingerprint ───────────────────────────────────────────
        fp = FingerprintService()
        sel = results[0]
        xs = []
        for _ in range(args.runs):
            t = time.perf_counter()
            f = fp.create_fingerprint(sel, input_image_bytes=img_bytes, matching=m)
            xs.append((time.perf_counter() - t) * 1000)
        rows.append(report("3 fingerprint (SHA-256)", xs))

        # ── stage 4/5: chain write + read-back (in-memory) ──────────────────
        chain = LocalBlockchainProvider()
        bc = BlockchainService(chain)
        xs_w, xs_r, xs_v = [], [], []
        ver = VerificationService(fp)
        for _ in range(args.runs):
            t = time.perf_counter()
            rec = await bc.register(f.value, sel.url)
            xs_w.append((time.perf_counter() - t) * 1000)

            t = time.perf_counter()
            oc = await bc.get_record(rec.record_id)
            xs_r.append((time.perf_counter() - t) * 1000)

            t = time.perf_counter()
            ver.verify(canonical_data=f.canonical_data,
                       on_chain_fingerprint=oc.fingerprint,
                       record_id=rec.record_id)
            xs_v.append((time.perf_counter() - t) * 1000)
        rows.append(report("4 chain write (in-memory)", xs_w))
        rows.append(report("5 chain read-back", xs_r))
        rows.append(report("6 verify (recompute+compare)", xs_v))

        # ── where the time actually goes ───────────────────────────────────
        print()
        print("=" * 92)
        print("SHARE OF TOTAL")
        print("=" * 92)
        total = sum(r["median"] for r in rows)
        for r in rows:
            share = 100 * r["median"] / total if total else 0
            bar = "#" * int(round(share / 2))
            print(f"  {r['stage']:<34} {r['median']:9.1f} ms  {share:5.1f}%  {bar}")
        print(f"  {'TOTAL (local, 12 candidates)':<34} {total:9.1f} ms")

        print()
        print(f"  per-candidate encode median : {per_candidate:.0f} ms")
        print(f"  => extrapolated matching at 60 candidates, concurrency "
              f"{settings.MATCH_CONCURRENCY}: "
              f"~{matching_median * 60 / args.candidates / 1000:.0f} s")

        # ── concurrency sweep ──────────────────────────────────────────────
        if args.concurrency_sweep:
            print()
            print("=" * 92)
            print("CONCURRENCY SWEEP  (does more parallelism actually help?)")
            print("=" * 92)
            print("  ONNX already uses all cores per inference, so workers contend.")
            for c in (1, 2, 4, 8, 12):
                s2 = settings.model_copy(update={"MATCH_CONCURRENCY": c})
                mm = MatchingService(s2)
                fresh = [r.model_copy(deep=True) for r in results]
                t = time.perf_counter()
                await mm.match(embedding, fresh)
                el = (time.perf_counter() - t) * 1000
                print(f"  concurrency {c:<3} -> {el:8.1f} ms   "
                      f"({el / args.candidates:6.1f} ms/candidate)")
    finally:
        srv.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
