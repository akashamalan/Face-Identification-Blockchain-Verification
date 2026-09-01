"""End-to-end pipeline orchestrator.

Executes the full flow: face → search → fingerprint → blockchain → verify.
Measures timing for each stage and returns a complete PipelineResult.
"""

from __future__ import annotations

import time
import uuid

from app.core.logging import get_logger
from app.models.domain import PipelineResult
from app.services.face_service import FaceService
from app.services.search_service import SearchService
from app.services.fingerprint_service import FingerprintService
from app.services.blockchain_service import BlockchainService
from app.services.verification_service import VerificationService

log = get_logger(__name__)


class PipelineService:
    def __init__(
        self,
        face_service: FaceService,
        search_service: SearchService,
        fingerprint_service: FingerprintService,
        blockchain_service: BlockchainService,
        verification_service: VerificationService,
    ):
        self._face = face_service
        self._search = search_service
        self._fingerprint = fingerprint_service
        self._blockchain = blockchain_service
        self._verification = verification_service

    async def run(self, image_bytes: bytes, filename: str = "image.jpg") -> PipelineResult:
        pipeline_id = uuid.uuid4().hex[:12]
        t_total = time.perf_counter()

        log.info("Pipeline %s: starting", pipeline_id)

        result = PipelineResult(pipeline_id=pipeline_id)

        try:
            # ── Stage 1: Face Detection ──────────────────────────────────
            log.info("Pipeline %s: detecting face", pipeline_id)
            face_data = self._face.detect(image_bytes, allow_multiple=False)
            result.face = face_data

            # ── Stage 2: Reverse Image Search ────────────────────────────
            log.info("Pipeline %s: searching", pipeline_id)
            search_response = await self._search.reverse_image_search(
                image_bytes, filename=filename
            )
            result.search = search_response

            if not search_response.selected_result:
                result.status = "error"
                result.error = "No matching result found."
                return result

            selected = search_response.selected_result

            # ── Stage 3: Fingerprint ─────────────────────────────────────
            log.info("Pipeline %s: generating fingerprint", pipeline_id)
            fingerprint = self._fingerprint.create_fingerprint(selected)
            result.fingerprint = fingerprint

            # ── Stage 4: Blockchain Registration ─────────────────────────
            log.info("Pipeline %s: registering on blockchain", pipeline_id)
            bc_record = await self._blockchain.register(
                fingerprint.value, selected.url
            )
            result.blockchain = bc_record

            # ── Stage 5: Verification ────────────────────────────────────
            log.info("Pipeline %s: verifying", pipeline_id)
            verification = self._verification.verify(
                canonical_data=fingerprint.canonical_data,
                on_chain_fingerprint=bc_record.fingerprint,
                transaction_hash=bc_record.transaction_hash,
            )
            result.verification = verification

            result.status = "success"
            total_ms = (time.perf_counter() - t_total) * 1000
            result.total_time_ms = round(total_ms, 1)

            log.info(
                "Pipeline %s: completed in %.0fms — %s",
                pipeline_id,
                total_ms,
                verification.status,
            )

        except Exception as exc:
            total_ms = (time.perf_counter() - t_total) * 1000
            result.total_time_ms = round(total_ms, 1)
            result.status = "error"
            result.error = str(exc)
            log.error("Pipeline %s: failed — %s", pipeline_id, exc)
            raise

        return result
