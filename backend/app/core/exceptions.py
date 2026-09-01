"""Custom exception hierarchy for the pipeline."""

from __future__ import annotations


class PipelineBaseError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ── Face errors ──────────────────────────────────────────────────────────

class InvalidImageError(PipelineBaseError):
    def __init__(self, message: str = "The uploaded file is not a valid image."):
        super().__init__(message, code="INVALID_IMAGE")


class FaceDetectionError(PipelineBaseError):
    def __init__(self, message: str = "Face detection failed."):
        super().__init__(message, code="FACE_DETECTION_FAILED")


class NoFaceDetectedError(PipelineBaseError):
    def __init__(self, message: str = "No face was detected in the uploaded image."):
        super().__init__(message, code="FACE_NOT_FOUND")


class MultipleFacesError(PipelineBaseError):
    def __init__(self, count: int = 0):
        super().__init__(
            f"Expected exactly 1 face but detected {count}. Please upload an image with a single face.",
            code="MULTIPLE_FACES",
        )


class FaceEncodingError(PipelineBaseError):
    def __init__(self, message: str = "Failed to generate face encoding."):
        super().__init__(message, code="FACE_ENCODING_FAILED")


# ── Search errors ────────────────────────────────────────────────────────

class SearchProviderError(PipelineBaseError):
    def __init__(self, message: str = "Search provider returned an error."):
        super().__init__(message, code="SEARCH_ERROR")


class SearchTimeoutError(PipelineBaseError):
    def __init__(self, message: str = "Search request timed out."):
        super().__init__(message, code="SEARCH_TIMEOUT")


class SearchNotConfiguredError(PipelineBaseError):
    def __init__(self, message: str = "Search provider is not configured. Set SERPAPI_API_KEY."):
        super().__init__(message, code="SEARCH_NOT_CONFIGURED")


class NoSearchResultsError(PipelineBaseError):
    def __init__(self, message: str = "No matching public result was found."):
        super().__init__(message, code="NO_SEARCH_RESULTS")


# ── Blockchain errors ───────────────────────────────────────────────────

class BlockchainError(PipelineBaseError):
    def __init__(self, message: str = "Blockchain operation failed."):
        super().__init__(message, code="BLOCKCHAIN_ERROR")


class BlockchainNotConfiguredError(PipelineBaseError):
    def __init__(self, message: str = "Blockchain is not configured. Set RPC_URL, PRIVATE_KEY, and CONTRACT_ADDRESS."):
        super().__init__(message, code="BLOCKCHAIN_NOT_CONFIGURED")


# ── Verification errors ─────────────────────────────────────────────────

class VerificationError(PipelineBaseError):
    def __init__(self, message: str = "Verification failed."):
        super().__init__(message, code="VERIFICATION_ERROR")


class RecordNotFoundError(PipelineBaseError):
    def __init__(self, record_id: str = ""):
        super().__init__(
            f"No blockchain record found for id: {record_id}",
            code="RECORD_NOT_FOUND",
        )
