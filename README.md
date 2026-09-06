# Face Identification & Blockchain Verification

Find where a face appears online — and prove the search was honest.

---

## About This Project

Imagine someone shows you a screenshot and says *"my software found this
person's Instagram."* Two fair questions:

1. **Did it really match, or did the search engine just guess?**
2. **Did you pick that result afterwards to make the demo look good?**

Normally you'd have to take their word for it. This project doesn't ask
you to.

**What it does, in plain terms:**

You give it a photo of a face. It searches the web to find where that
face appears. Then — and this is the part most tools skip — it
**downloads every result and checks the face again itself**, instead of
trusting whatever the search engine ranked first.

Finally, it takes a digital fingerprint of everything it found and writes
that fingerprint onto a blockchain: a public record that nobody, not even
me, can quietly change later.

**Who this is for:** anyone who needs to prove a search result is genuine
— journalists checking a source, someone verifying their own online
presence, or a reviewer who wants to confirm a result wasn't cherry-picked.

Built for Hacker House Goa 2026, Task 3.

---

## Quick Start

### Prerequisites

- [ ] Python 3.11 or newer
- [ ] Node.js 18+ *(only if you want the local interface — optional)*
- [ ] A free [SerpAPI](https://serpapi.com) key (reverse image search)
- [ ] A free [Alchemy](https://alchemy.com) account (blockchain access)
- [ ] A **throwaway** crypto wallet with free Sepolia test funds
- [ ] ~1 GB free disk — the face model downloads on first run

> ⚠️ **Never use a wallet holding real money.** Create a fresh one. The
> private key sits in a plain text file, and this network uses free test
> currency only.

### 1. Clone and set up the backend

```bash
git clone https://github.com/akashamalan/Face-Identification-Blockchain-Verification.git
cd Face-Identification-Blockchain-Verification/backend

# Create a fresh virtual environment for THIS project
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Mac / Linux
# source venv/bin/activate

# Verify that Python comes from this project's venv
python --version
where.exe python          # Windows
# which python            # Mac / Linux

# Install dependencies
python -m pip install -r requirements.txt
```

### 2. Add your keys

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # Mac / Linux
```

Open `.env` and fill in:

| Key | Where to get it |
|---|---|
| `SERPAPI_API_KEY` | serpapi.com dashboard |
| `BLOCKCHAIN_RPC_URL` | Alchemy → your app → Endpoints → Sepolia HTTPS |
| `BLOCKCHAIN_PRIVATE_KEY` | MetaMask → Account details → Show private key |
| `BLOCKCHAIN_PROVIDER` | set to `ethereum` |
| `CONTRACT_ADDRESS` | leave blank — step 3 gives you this |

### 3. Deploy the smart contract

```bash
python scripts/deploy_contract.py
```

Copy the address it prints into `CONTRACT_ADDRESS` in `.env`.

### 4. Run it

```bash
uvicorn app.main:app --port 8000
```

Open **http://localhost:8000/docs** in your browser. That's the full
pipeline — upload a face to `/api/pipeline/run` and watch every stage.

> This runs entirely on your own machine. Nothing is hosted or exposed
> to the internet.

### 5. Optional — the local interface

```bash
cd ../frontend
npm install
npm run dev
```

Open **http://localhost:5173** for a friendlier view with per-stage
timings and the full candidate list.

---

## Blockchain Used

**Ethereum Sepolia** — a public test network.

### Why Sepolia and not the others

| Blockchain | Key feature for this project | Trade-off considered |
|---|---|---|
| **Ethereum Sepolia** ✅ | Public, permanent, free test currency, and anyone can independently verify a record on Etherscan without trusting me | Test network — records are real and public but carry no economic security |
| Ethereum Mainnet | Strongest guarantees in existence | Every write costs real money. Unjustifiable for a demo. |
| Polygon Amoy | Cheaper, faster, easier faucets | Fewer independent verifiers; explorer less familiar to reviewers |
| Solana | Very fast, very cheap | Different toolchain entirely; Rust rewrite for no benefit here |
| Local / simulated chain | Zero setup, zero cost | **Nobody else can check it.** That defeats the whole purpose. |

**The deciding factor:** the point of this project is that *a stranger
can verify the record themselves*. A local chain would have been far
easier — and would have proven nothing. Sepolia is the cheapest option
where the verification is genuinely independent.

**What actually goes on chain:** only a SHA-256 fingerprint and the
source URL. **No images. No face data. No personal information.**

---

## How It Works

```
        your face photo
              │
              ▼
   ┌──────────────────────┐
   │ 1. DETECT & ENCODE   │  InsightFace turns the face into
   │                      │  512 numbers that describe it
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ 2. SEARCH THE WEB    │  Google Lens returns ~50 places
   │                      │  this image might appear
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ 3. CHECK EVERY ONE   │  ⭐ downloads each result, reads
   │    OURSELVES         │  its face, scores the similarity
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ 4. FINGERPRINT       │  one SHA-256 hash covering the
   │                      │  match AND every rejected result
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ 5. WRITE TO CHAIN    │  signed transaction on Sepolia
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ 6. READ BACK & CHECK │  fetch from chain, recompute,
   │                      │  compare. Match = VERIFIED
   └──────────────────────┘
```

### Why step 3 matters

Most tools stop at step 2 and report whatever the search engine ranked
first. In a real run of this pipeline, **Google Lens ranked a complete
stranger #1**. The correct person was at **position #4**, and won on a
measured similarity of **0.9935**.

Trusting the search engine would have returned the wrong person with
total confidence.

### Why step 4 is unusual

The fingerprint doesn't just cover the winner — it covers **every
candidate**, in the order the search returned them, with each score and
each accept/reject decision:

```
[0] sim=  --    skipped   no face detected in candidate image
[1] sim=  --    skipped   download failed: HTTP 404
[2] sim=  --    skipped   no usable image URL
[3] sim=0.9935  accepted  similarity 0.9935 >= threshold 0.400
```

Reorder that list, drop a losing candidate, or alter a rejected one — and
the fingerprint changes, so verification fails.

**This makes the search itself checkable, not just its answer.**

### The matching threshold: 0.400

Not guessed. Measured on **100 same-person and 100 different-person
photo pairs** from the LFW dataset:

| | median score | worst case |
|---|---|---|
| same person | 0.689 | 0.101 |
| different person | 0.005 | 0.119 |

The statistically "optimal" cutoff was 0.120 — but that sits **0.0006**
above the worst wrong-person score. No safety margin at all.

Accuracy stays flat all the way from 0.12 to 0.40, so **0.400** was
chosen: the largest possible safety margin at no cost in accuracy.

Reproduce it yourself: `python scripts/calibrate_threshold.py`

---

## Known Limitations

| Limitation | Impact | Workaround / plan |
|---|---|---|
| A visual match is not proof of identity. Lookalikes exist. | **High** | Threshold set deliberately high; below it, the system returns "no confident match" rather than guessing |
| If Google Lens finds nothing, the pipeline can't match | **High** | Coverage limit, not an accuracy one. Adding a second search provider would help |
| Threshold calibrated on LFW, which is cleaner than real web images | **Medium** | Real scores run lower, so it fails toward "no match" — the safe direction |
| Many search results have no usable image to download | **Medium** | Skipped and *recorded as skipped* in the audit bundle, never silently dropped |
| Sepolia is a test network | **Medium** | Records are real and public but carry no economic security. Mainnet is a config change |
| SerpAPI free tier is ~100 searches/month | **Low** | A mock provider is included for development |
| First run downloads a ~300 MB model | **Low** | One-time; cached afterwards |

---

## Ethics and Scope

**This is built for verifying consenting subjects — not for identifying
strangers.**

The demo uses the author's own face. It processes only publicly available
content, and stores only a hash on the blockchain — never images, never
face data, never personal information.

Face search technology can be used to stalk people. That's a real risk,
and scoping this to consenting subjects is a deliberate choice, not an
afterthought.

---

## Glossary

| Term | In everyday language |
|---|---|
| **Face embedding** | A list of 512 numbers describing a face. Similar faces produce similar numbers. |
| **Cosine similarity** | How alike two of those number-lists are. 1.0 = identical, 0.0 = unrelated. |
| **Threshold** | The score above which we say "same person." Ours is 0.400. |
| **SHA-256 / hash / fingerprint** | A short code produced from data. Change one letter of the data and the code changes completely. |
| **Blockchain** | A public record that anyone can read and nobody can secretly edit. |
| **Testnet** | A practice blockchain using free, worthless currency. Real mechanics, no cost. |
| **Smart contract** | A small program living on the blockchain. Ours just stores and returns fingerprints. |
| **Wallet / private key** | Your blockchain account and its password. |
| **Gas** | The small fee for writing to a blockchain. Free on a testnet. |
| **Tamper-evident** | You can't stop someone changing data — but you can always *tell* that they did. |
| **Audit bundle** | The full list of every candidate considered, with scores and decisions. |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `insufficient funds` on deploy | Wallet is empty. Get free Sepolia ETH from a faucet. |
| Model download hangs on first run | ~300 MB over your connection. Give it a few minutes. |
| `No face detected` | Photo needs one clear, reasonably sized face. |
| SerpAPI 429 | Monthly free quota hit. Switch to the mock provider. |
| `ModuleNotFoundError` | Virtual environment isn't activated. |

---

## Tech Stack

FastAPI · InsightFace (buffalo_l) · SerpAPI Google Lens · web3.py ·
Solidity 0.8.19 · React + Vite + TypeScript

Run the tests: `pytest` from `backend/`
```

Two things before you push: swap the demo photo for **your own face**, and confirm `.env` is not tracked — `git ls-files | findstr .env` should show only `.env.example`.
