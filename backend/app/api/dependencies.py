"""FastAPI dependency injection — creates and caches service instances."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.providers.blockchain.base import BlockchainProvider
from app.providers.search.base import SearchProvider
from app.services.blockchain_service import BlockchainService
from app.services.face_service import FaceService
from app.services.fingerprint_service import FingerprintService
from app.services.pipeline_service import PipelineService
from app.services.search_service import SearchService
from app.services.verification_service import VerificationService


def _build_search_provider(settings: Settings) -> SearchProvider:
    if settings.SEARCH_PROVIDER == "mock":
        from app.providers.search.mock_provider import MockSearchProvider
        return MockSearchProvider()
    from app.providers.search.serpapi_provider import SerpApiSearchProvider
    return SerpApiSearchProvider(
        api_key=settings.SERPAPI_API_KEY,
        timeout=settings.SEARCH_TIMEOUT_SECONDS,
    )


def _build_blockchain_provider(settings: Settings) -> BlockchainProvider:
    if settings.BLOCKCHAIN_PROVIDER == "local":
        from app.providers.blockchain.local_provider import LocalBlockchainProvider
        return LocalBlockchainProvider()
    from app.providers.blockchain.ethereum_provider import EthereumProvider
    return EthereumProvider(
        rpc_url=settings.BLOCKCHAIN_RPC_URL,
        private_key=settings.BLOCKCHAIN_PRIVATE_KEY,
        contract_address=settings.CONTRACT_ADDRESS,
        chain_id=settings.CHAIN_ID,
        timeout=settings.BLOCKCHAIN_TIMEOUT_SECONDS,
    )


# ── Singletons ───────────────────────────────────────────────────────────

_search_provider: SearchProvider | None = None
_blockchain_provider: BlockchainProvider | None = None


def get_face_service() -> FaceService:
    return FaceService(get_settings())


def get_search_provider() -> SearchProvider:
    global _search_provider
    if _search_provider is None:
        _search_provider = _build_search_provider(get_settings())
    return _search_provider


def get_blockchain_provider() -> BlockchainProvider:
    global _blockchain_provider
    if _blockchain_provider is None:
        _blockchain_provider = _build_blockchain_provider(get_settings())
    return _blockchain_provider


def get_search_service() -> SearchService:
    return SearchService(get_search_provider())


def get_fingerprint_service() -> FingerprintService:
    return FingerprintService()


def get_blockchain_service() -> BlockchainService:
    return BlockchainService(get_blockchain_provider())


def get_verification_service() -> VerificationService:
    return VerificationService(get_fingerprint_service())


def get_pipeline_service() -> PipelineService:
    return PipelineService(
        face_service=get_face_service(),
        search_service=get_search_service(),
        fingerprint_service=get_fingerprint_service(),
        blockchain_service=get_blockchain_service(),
        verification_service=get_verification_service(),
    )
