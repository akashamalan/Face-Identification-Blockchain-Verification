# Face Verification Pipeline

**Hacker House Goa 2026 — Task 3**

> Face Identification + Web/Social Search + Blockchain Verification

## Overview

An end-to-end pipeline that accepts a face image, performs a genuine reverse-image
web search, extracts post data, creates a cryptographic fingerprint, stores it on
the Ethereum blockchain, and verifies data integrity by comparing recomputed hashes
against on-chain records.

## Problem

How do you prove that publicly discovered web content about a person has not been
tampered with after it was found? This system provides cryptographic proof by
anchoring content fingerprints on an immutable blockchain.

## Solution

A pipeline that chains face detection → reverse image search → data extraction →
SHA-256 fingerprinting → Ethereum blockchain registration → tamper-proof verification.

## Architecture

```
FACE IMAGE
    │
    ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  InsightFace    │────▶│  SerpAPI Google   │────▶│  SHA-256 Hash     │
│  Detection +    │     │  Lens Reverse     │     │  Canonical JSON   │
│  Encoding       │     │  Image Search     │     │  Fingerprint      │
└─────────────────┘     └──────────────────┘     └─────────┬─────────┘
                                                           │
                                                           ▼
                                                 ┌───────────────────┐
                                                 │  Ethereum Sepolia │
                                                 │  Smart Contract   │
                                                 │  Registration     │
                                                 └─────────┬─────────┘
                                                           │
                                                           ▼
                                                 ┌───────────────────┐
                                                 │  Recompute Hash   │
                                                 │  Compare with     │
                                                 │  On-Chain Record  │
                                                 └─────────┬─────────┘
                                                           │
                                              ┌────────────┴────────────┐
                                              │                         │
                                          VERIFIED                  TAMPERED
```

## Pipeline

1. **Face Scan** — Upload image with a face
2. **Face Detection** — InsightFace detects and validates exactly one face
3. **Face Encoding** — 512-d embedding generated (not stored or exposed)
4. **Reverse Image Search** — SerpAPI Google Lens searches the public web
5. **Result Selection** — Best match selected (social media prioritized)
6. **SHA-256 Fingerprint** — Canonical JSON serialized and hashed
7. **Blockchain Registration** — Fingerprint stored on Ethereum Sepolia
8. **Verification** — Recompute hash and compare with on-chain record

## Features

- ✅ Real face detection with InsightFace
- ✅ Genuine reverse-image search via SerpAPI
- ✅ Deterministic SHA-256 fingerprinting
- ✅ Ethereum Sepolia blockchain registration
- ✅ Tamper detection (VERIFIED / TAMPERED)
- ✅ React frontend with live pipeline visualization
- ✅ Provider abstraction (swappable search + blockchain)
- ✅ Comprehensive error handling
- ✅ Privacy-focused (no permanent image storage)

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Face Processing | InsightFace, ONNX Runtime, OpenCV |
| Search | SerpAPI (Google Lens) |
| Blockchain | Web3.py, Ethereum Sepolia |
| Hashing | SHA-256 |
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Smart Contract | Solidity 0.8.19 |

## Project Structure

```
face-verify-pipeline/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI endpoints
│   │   ├── core/                # Config, logging, exceptions, security
│   │   ├── models/              # Pydantic domain/request/response models
│   │   ├── providers/           # External service integrations
│   │   │   ├── face/            # InsightFace provider
│   │   │   ├── search/          # SerpAPI + mock providers
│   │   │   └── blockchain/      # Ethereum + local providers
│   │   ├── services/            # Business logic layer
│   │   └── utils/               # Hashing, validation, cleanup
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    # React + Vite + TypeScript
├── contracts/                   # Solidity smart contract
├── scripts/                     # Deployment scripts
├── docs/                        # Architecture, API, limitations
├── docker-compose.yml
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Environment Variables

Copy the example env files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` with your credentials:

```env
# Search — Get at https://serpapi.com (free: 100 searches/month)
SERPAPI_API_KEY=your_serpapi_key_here

# Blockchain — Get at https://dashboard.alchemy.com (free tier)
BLOCKCHAIN_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
BLOCKCHAIN_PRIVATE_KEY=your_metamask_private_key
CONTRACT_ADDRESS=your_deployed_contract_address
CHAIN_ID=11155111
```

### Installation

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

## Smart Contract Deployment

### Option A: Remix IDE (Recommended for demos)

1. Open [remix.ethereum.org](https://remix.ethereum.org)
2. Create a new file: `VerificationRegistry.sol`
3. Paste the contents of `contracts/VerificationRegistry.sol`
4. Compile with Solidity 0.8.19
5. Connect MetaMask (Sepolia network)
6. Deploy the contract
7. Copy the contract address to `backend/.env` → `CONTRACT_ADDRESS`

### Option B: Script deployment

```bash
pip install py-solc-x
python scripts/deploy_contract.py
```

### Getting Sepolia ETH

Get free testnet ETH from:
- https://sepoliafaucet.com
- https://faucets.chain.link/sepolia

## Running Locally

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Open http://localhost:5173

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Full docs: `docs/api.md`

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

Unit tests cover:
- SHA-256 determinism and canonicalization
- Fingerprint generation
- VERIFIED / TAMPERED verification logic
- Search result normalization
- API endpoint validation
- Blockchain lifecycle (local provider)

## Canonicalization Algorithm

The SHA-256 fingerprint is computed as follows:

1. Extract fields: `url`, `title`, `domain`, `snippet`, `image_url`, `metadata`
2. Recursively sort all dictionary keys alphabetically
3. Strip leading/trailing whitespace from all string values
4. Collapse internal whitespace to single spaces
5. Serialize to JSON with `sort_keys=True`, `separators=(',', ':')`
6. Encode to UTF-8 bytes
7. Compute `SHA-256(bytes).hexdigest()`

No timestamps or random values are included in the hash input.

## Blockchain

- **Network**: Ethereum Sepolia testnet (chain ID 11155111)
- **Contract**: `VerificationRegistry` — stores fingerprint hashes
- **Stored data**: SHA-256 fingerprint (bytes32), source URL, timestamp, submitter
- **NOT stored**: Face images, embeddings, personal data
- **Verification**: Recompute hash locally → compare with on-chain record

## Security

- CORS restricted to configured origins
- File upload validation (type, size, magic bytes)
- Private keys loaded from environment only
- No secrets in frontend, logs, or API responses
- Temporary file cleanup after processing
- Structured error responses (no stack traces)
- Pydantic input validation

## Privacy

- Images processed temporarily in memory
- No permanent image storage
- No covert surveillance capabilities
- Only publicly accessible content is processed
- On-chain: only hashes and URLs (no personal data)
- Face embeddings never logged or exposed via API

## Known Limitations

See `docs/limitations.md` for full details.

- SerpAPI free tier: 100 searches/month
- Google Lens may return zero results for uncommon images
- Blockchain confirmations take 15–60 seconds
- Face detection may fail in poor lighting/angles
- Visual match ≠ identity verification

## Demo Instructions (60–90 seconds)

1. **Start backend**: `cd backend && uvicorn app.main:app --reload`
2. **Start frontend**: `cd frontend && npm run dev`
3. **Open** http://localhost:5173
4. **Verify** green "All systems ready" status bar
5. **Upload** a publicly recognizable face image
6. **Watch** the pipeline stages animate:
   - ✓ Face Detected
   - ✓ Search Results Found
   - ✓ Fingerprint Generated
   - ✓ Blockchain Recorded
   - ✓ **VERIFIED**
7. **Point out**:
   - The discovered URL and platform
   - The SHA-256 fingerprint
   - The blockchain transaction hash
   - The Etherscan link
   - The VERIFIED badge with matching hashes
8. **Explain**: "If anyone modifies the discovered data, the recomputed hash
   won't match the blockchain record, and the status changes to TAMPERED."

## License

MIT — See [LICENSE](./LICENSE)
