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
│  InsightFace    │────▶│  SerpAPI Google   │────▶│  RE-ENCODE each   │
│  Detection +    │     │  Lens Reverse     │     │  candidate image  │
│  Encoding       │     │  Image Search     │     │  + cosine score   │
└─────────────────┘     └──────────────────┘     └─────────┬─────────┘
                                                           │
                                    below threshold ◀──────┤
                                  (no_confident_match)     │
                                                           ▼
                                                 ┌───────────────────┐
                                                 │  SHA-256 Hash     │
                                                 │  metadata + image │
                                                 │  digests + audit  │
                                                 │  bundle digest    │
                                                 └─────────┬─────────┘
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
                                                 │  READ BACK by     │
                                                 │  record_id, then  │
                                                 │  recompute + cmp  │
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
5. **Candidate Re-encoding & Scoring** — every candidate image is downloaded,
   re-encoded with the same model, and cosine-scored against the input face.
   Selection is by **similarity**, not by Lens position. Below threshold the
   pipeline returns `no_confident_match` and registers nothing.
6. **SHA-256 Fingerprint** — canonical JSON over the search metadata **plus** the
   input image digest, the matched image digest, and the candidate audit bundle digest
7. **Blockchain Registration** — Fingerprint stored on Ethereum Sepolia
8. **Blockchain Read-back** — the record is fetched from chain by its `record_id`
9. **Verification** — recomputed hash compared against the value read back from chain

## Candidate matching — the accuracy stage

Google Lens returns *visually similar* images. Visual similarity is not identity, so
Lens ordering is treated as a hint and never as evidence. `MatchingService`
(`backend/app/services/matching_service.py`) downloads each candidate image
(`image_url`, falling back to `thumbnail`), re-encodes it with the same `buffalo_l`
model used on the input, and computes cosine similarity against the input embedding.

- Downloads are bounded: `MATCH_CONCURRENCY` (4), `MATCH_DOWNLOAD_TIMEOUT_SECONDS`
  (10), `MATCH_MAX_IMAGE_BYTES` (8 MiB, enforced mid-stream so a server that lies
  about `content-length` cannot make us buffer an unbounded body), and
  `MATCH_MAX_CANDIDATES` (15).
- Candidates with no usable image, a failed download, or no detectable face are
  **skipped with a recorded reason** — not treated as errors. Lens routinely returns
  logos, product shots and screenshots.
- Candidate images containing several people are scored against *every* detected face,
  keeping the best, so a group photo containing the subject is not discarded.

### Measured threshold: **0.40**

Not guessed. `scripts/calibrate_threshold.py` measures it against **LFW official
labelled pairs** (`sklearn.datasets.fetch_lfw_pairs`), where "same" means two
*different photographs* of one person — the situation the pipeline actually faces.
Full sweep in `docs/threshold_calibration.json`.

Augmenting a single image would not work here: near-identical copies score ~0.95+,
inflating the same-person distribution and yielding a falsely wide gap.

`n = 100` same-person pairs, `n = 100` different-person pairs, cosine on
`buffalo_l` / `w600k_r50`, 0 pairs discarded for non-detection:

| | min | p05 | p25 | median | p75 | p95 | max | mean | sd |
|---|---|---|---|---|---|---|---|---|---|
| **same person** | 0.1005 | 0.4891 | 0.6262 | 0.6890 | 0.7342 | 0.8302 | 0.9048 | 0.6712 | 0.1141 |
| **different person** | −0.1079 | −0.0840 | −0.0323 | 0.0046 | 0.0428 | 0.0966 | 0.1194 | 0.0077 | 0.0527 |

```
         range  same-person                                different-person
[-0.15,-0.10)                                             ##
[-0.10,-0.05)                                             ###########
[-0.05,-0.00)                                             ########################################
[-0.00,+0.05)                                             ##################################
[+0.05,+0.10)                                             #####################
[+0.10,+0.15)  #                                          ######
[+0.40,+0.45)  ##
[+0.45,+0.50)  #########
[+0.50,+0.55)  #####
[+0.55,+0.60)  ###
[+0.60,+0.65)  ################
[+0.65,+0.70)  ##########################
[+0.70,+0.75)  ###############################
[+0.75,+0.80)  #########
[+0.80,+0.85)  ##########
[+0.90,+0.95)  #
```

The classes are almost fully separated; they touch only in `[0.10, 0.12)` because of a
single same-person outlier at 0.1005.

**Why 0.40 and not the statistically "optimal" value.** Youden's J peaks at **0.120**
— but that sits 0.0006 above the highest observed different-person score (0.1194),
i.e. essentially zero safety margin on a 100-pair sample. The sweep shows performance
is *flat* across a wide band, so there is no cost to being far more conservative:

| threshold | TPR | FPR | missed | false accepts | margin over worst different-person |
|---|---|---|---|---|---|
| 0.120 | 0.990 | 0.000 | 1 | 0 | +0.0006 |
| 0.200 | 0.990 | 0.000 | 1 | 0 | +0.0806 |
| 0.300 | 0.990 | 0.000 | 1 | 0 | +0.1806 |
| **0.400** | **0.990** | **0.000** | **1** | **0** | **+0.2806** |
| 0.450 | 0.970 | 0.000 | 3 | 0 | +0.3306 |
| 0.500 | 0.890 | 0.000 | 11 | 0 | +0.3806 |
| 0.600 | 0.820 | 0.000 | 18 | 0 | +0.4806 |

0.40 is the **top of the plateau**: the last threshold retaining maximum measured
sensitivity (TPR 0.990), while sitting 7.4 standard deviations above the
different-person mean. Past 0.40 recall degrades with no reduction in false accepts,
because FPR is already 0.

**Caveats, stated honestly.** LFW is frontal and funneled — easier than arbitrary web
images. Real Lens results carry more pose, lighting and resolution variation, so
production same-person scores will run *lower* than LFW's 0.689 median. A hard
same-person pair falling under 0.40 yields `no_confident_match`, which is the safe
direction to fail for this application: refusing to name someone beats naming the
wrong person. Re-measure with `--pairs 500` if you want tighter tail estimates.

Reproduce:

```bash
backend/venv/Scripts/python.exe -m pip install scikit-learn
backend/venv/Scripts/python.exe scripts/calibrate_threshold.py --pairs 100
```

`scikit-learn` is a **dev-only** dependency and is deliberately absent from
`backend/requirements.txt` — nothing at runtime imports it.

## Candidate audit bundle

The fingerprint covers the **whole search**, not just the winner. Every candidate the
search returned gets a `CandidateEvidence` record, in the order it was returned:

```
[0] sim=  --    skipped                    no face detected in candidate image
[1] sim=  --    skipped                    download failed: HTTP 404
[2] sim=  --    skipped                    no image_url or thumbnail on this result
[3] sim=0.9935  accepted                   similarity 0.9935 >= threshold 0.400
```

`audit_bundle_sha256` is the SHA-256 of that ordered list, and it goes into the
canonical data that is hashed and written on-chain. Consequences:

- Reordering candidates changes the digest.
- Dropping a candidate changes the digest.
- Altering a **losing** candidate's score changes the digest.

So the on-chain record does not merely assert "this result was registered" — it commits
to *which candidates were considered, what each scored, and why each was accepted or
rejected*. A verifier can confirm the winner was chosen on similarity and that nothing
was cherry-picked. This is what makes the search step cryptographically genuine rather
than a hardcoded result. Tests: `backend/tests/unit/test_fingerprint_coverage.py`,
`backend/tests/integration/test_matching.py`.

The bundle itself is returned in the pipeline response and must be archived alongside
the record; the on-chain digest anchors it but does not store it (only the 32-byte
fingerprint is written).

## Features

- ✅ Real face detection with InsightFace
- ✅ Genuine reverse-image search via SerpAPI
- ✅ Candidate images re-encoded and cosine-scored against the input face
- ✅ Measured (not guessed) similarity threshold, with published evidence
- ✅ "No confident match" as a first-class outcome
- ✅ Cryptographic audit bundle over every candidate considered
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

1. Extract fields: `url`, `title`, `domain`, `snippet`, `image_url`, `metadata`,
   `input_image_sha256`, `matched_image_sha256`, `audit_bundle_sha256`,
   `match_similarity`, `match_threshold`
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
- Visual match ≠ identity verification (which is why stage 5 re-scores candidates)
- Threshold measured on LFW; real web images are harder than LFW

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
