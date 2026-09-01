# 60–90 Second Demo Guide — Hacker House Goa 2026 Task 3

This document contains the exact step-by-step judge demonstration procedure for **Face Identification + Web/Social Search + Blockchain Verification**.

---

## Pre-Demo Checklist

1. **Start Backend Server**:
   ```bash
   cd backend
   venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Frontend App**:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open Web UI in Browser: `http://localhost:5173`

---

## 90-Second Screen Recording / Judge Walkthrough

### Step 1: Preflight Readiness (10s)
- Look at the header bar on `http://localhost:5173`.
- Confirm `System Status: OK` and operational status indicators (`Face Engine: Ready`, `Search: Configured`, `Blockchain: Connected`).

### Step 2: Upload Face Image (15s)
- Drag and drop a sample face image (e.g., from `sample_data/` or any portrait image) into the upload area.
- Click **Run Verification Pipeline**.

### Step 3: Face Detection & Encoding (10s)
- Observe Stage 1 (**Face Detection**):
  - Validates single face presence.
  - Generates 512-d InsightFace embedding in memory.

### Step 4: Web / Reverse Image Search (15s)
- Observe Stage 2 (**Web Search**):
  - Performs genuine Google Lens search via SerpAPI (or mock provider in offline demo mode).
  - Retrieves real web and social media matches.
  - Displays selected source URL and title.

### Step 5: Canonical SHA-256 Fingerprinting (10s)
- Observe Stage 3 (**Fingerprint Generation**):
  - Normalizes extracted post metadata into canonical JSON format.
  - Generates deterministic 64-character SHA-256 hash.

### Step 6: Blockchain Registration & Retrieval (15s)
- Observe Stage 4 (**Blockchain Record**):
  - Submits fingerprint to Ethereum Sepolia testnet smart contract (`VerificationRegistry.sol`).
  - Retrieves block number, transaction hash, and stored fingerprint.

### Step 7: Local Hash Recomputation & Verification (15s)
- Observe Stage 5 (**Verification**):
  - Recomputes SHA-256 hash locally from discovered post data.
  - Compares local hash with on-chain record.
  - Visual status pill displays **VERIFIED** in green.

---

## Tampering Scenario Demonstration

To prove the system detects post-discovery data tampering:

1. **Automated Integration Test**:
   ```bash
   cd backend
   venv\Scripts\pytest.exe tests/integration/test_pipeline.py -k test_tampering_detection
   ```
2. **Explanation**:
   - The original post metadata produces fingerprint `H1`.
   - Modifying a single character in the title/metadata produces fingerprint `H2`.
   - Re-running verification compares `H2` against on-chain `H1`, producing an explicit `TAMPERED` response.
