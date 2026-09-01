# Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────┐   │
│  │  Upload   │→ │ Pipeline │→ │  Results  │→ │ Verified  │   │
│  │  Image    │  │  Status  │  │  Display  │  │  Badge    │   │
│  └──────────┘  └──────────┘  └───────────┘  └───────────┘   │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP / JSON
┌────────────────────────▼─────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                   │
│                                                              │
│  ┌─── API Layer ────────────────────────────────────────┐    │
│  │  /api/health  /api/face  /api/search  /api/pipeline  │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     │                                        │
│  ┌─── Service Layer ┴──────────────────────────────────┐     │
│  │  FaceService │ SearchService │ BlockchainService     │    │
│  │  FingerprintService │ VerificationService            │    │
│  │  PipelineService (orchestrator)                      │    │
│  └──────────────────┬──────────────────────────────────┘     │
│                     │                                        │
│  ┌─── Provider Layer ┴─────────────────────────────────┐     │
│  │  InsightFace │ SerpAPI │ Ethereum/Web3.py            │    │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐        ┌─────▼─────┐       ┌─────▼──────┐
    │InsightFace│       │  SerpAPI   │      │  Sepolia    │
    │  (local)  │       │  (cloud)   │      │  Testnet    │
    └──────────┘        └───────────┘       └────────────┘
```

## Layers

1. **API Layer**: FastAPI routes, request validation, CORS, error handling
2. **Service Layer**: Business logic, orchestration, timing
3. **Provider Layer**: External integrations behind abstract interfaces

## Design Decisions

- **Provider Abstraction**: All external services (search, blockchain) are behind
  abstract base classes. This enables testing with mock/local providers and
  makes it easy to swap implementations.

- **No Database**: The pipeline is stateless. Blockchain serves as the persistent
  store. Pipeline results are returned directly to the caller.

- **Lazy Model Loading**: InsightFace models are loaded on first use to avoid
  slow startup times and memory usage when face detection isn't needed.

- **Deterministic Hashing**: JSON canonicalization ensures identical data always
  produces the same SHA-256 fingerprint regardless of key ordering or whitespace.
