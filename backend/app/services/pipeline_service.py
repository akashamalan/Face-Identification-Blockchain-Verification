"""End-to-end pipeline orchestrator."""

from __future__ import annotations

import asyncio
import time
import uuid

from app.core.exceptions import VerificationError
from app.core.logging import get_logger
from app.models.domain import PipelineResult
from app.services.face_service import FaceService
from app.services.search_service import SearchService
from app.services.matching_service import MatchingService
from app.services.fingerprint_service import FingerprintService
from app.services.blockchain_service import BlockchainService
from app.services.verification_service import VerificationService

log = get_logger(__name__)


class PipelineService:
    def __init__(
        self,
        face_service: FaceService,
        search_service: SearchService,
        matching_service: MatchingService,
        fingerprint_service: FingerprintService,
        blockchain_service: BlockchainService,
        verification_service: VerificationService,
    ):
        self._face = face_service
        self._search = search_service
        self._matching = matching_service
        self._fingerprint = fingerprint_service
        self._blockchain = blockchain_service
        self._verification = verification_service

    async def run(self, image_bytes: bytes, filename: str = "image.jpg") -> PipelineResult:
        pipeline_id = uuid.uuid4().hex[:12]
        t_total = time.perf_counter()

        log.info("Pipeline %s: starting", pipeline_id)

        result = PipelineResult(pipeline_id=pipeline_id)

        try:
            # Search takes only the image bytes, so it does not depend on the
            # detection result. Running them concurrently takes the shorter of the
            # two off the critical path instead of paying for both in series.
            log.info("Pipeline %s: detecting face + searching (concurrent)", pipeline_id)
            t_par = time.perf_counter()
            detection, search_response = await asyncio.gather(
                self._face.detect(image_bytes, allow_multiple=False),
                self._search.reverse_image_search(image_bytes, filename=filename),
            )
            log.info(
                "Pipeline %s: stage=detect+search parallel_ms=%.1f "
                "detect_ms=%.1f search_ms=%.1f saved_ms=%.1f",
                pipeline_id,
                (time.perf_counter() - t_par) * 1000,
                detection.data.processing_time_ms,
                search_response.search_time_ms,
                min(detection.data.processing_time_ms, search_response.search_time_ms),
            )
            result.face = detection.data
            result.search = search_response

            if not search_response.selected_result:
                result.status = "error"
                result.error = "No matching result found."
                return result

            log.info("Pipeline %s: matching candidates", pipeline_id)
            matching, selected = await self._matching.match(
                detection.embedding, search_response.results
            )
            result.matching = matching
            result.search = search_response

            if selected is None:
                result.status = "no_confident_match"
                best = matching.best_similarity
                result.error = (
                    f"No confident match. Best similarity "
                    f"{best:.4f} < threshold {matching.threshold:.3f} "
                    f"({matching.candidates_scored}/{matching.candidates_total} "
                    f"candidates scorable)."
                    if best is not None else
                    f"No confident match: none of {matching.candidates_total} "
                    "candidates yielded a usable face image to compare against."
                )
                result.total_time_ms = round((time.perf_counter() - t_total) * 1000, 1)
                log.info("Pipeline %s: %s", pipeline_id, result.error)
                return result

            search_response.selected_result = selected

            log.info("Pipeline %s: generating fingerprint", pipeline_id)
            fingerprint = self._fingerprint.create_fingerprint(
                selected, input_image_bytes=image_bytes, matching=matching
            )
            result.fingerprint = fingerprint

            log.info("Pipeline %s: registering on blockchain", pipeline_id)
            bc_record = await self._blockchain.register(
                fingerprint.value, selected.url
            )
            result.blockchain = bc_record

            if not bc_record.record_id:
                raise VerificationError(
                    "Blockchain record has no record_id, so it cannot be read back "
                    "and verification cannot be independent."
                )

            log.info(
                "Pipeline %s: reading record %s back from chain",
                pipeline_id, bc_record.record_id[:16],
            )
            on_chain_record = await self._blockchain.get_record(bc_record.record_id)
            result.on_chain_record = on_chain_record

            log.info("Pipeline %s: verifying", pipeline_id)
            verification = self._verification.verify(
                canonical_data=fingerprint.canonical_data,
                on_chain_fingerprint=on_chain_record.fingerprint,
                transaction_hash=bc_record.transaction_hash,
                record_id=bc_record.record_id,
            )
            result.verification = verification

            if not verification.verified:
                result.status = "error"
                result.error = (
                    "Fingerprint read back from the chain does not match the "
                    "recomputed fingerprint (TAMPERED)."
                )
                result.total_time_ms = round((time.perf_counter() - t_total) * 1000, 1)
                return result

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
