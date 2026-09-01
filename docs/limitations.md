# Known Limitations

## Face Recognition

- **False positives/negatives**: InsightFace is a statistical model and may
  fail to detect faces in certain lighting, angles, or occlusion conditions.
- **Single-face requirement**: The pipeline requires exactly one face per image.
  Group photos are rejected.
- **Model download**: InsightFace's `buffalo_l` model (~300MB) is downloaded
  on first use and cached locally.

## Search (SerpAPI / Google Lens)

- **Rate limits**: Free SerpAPI tier allows 100 searches/month.
- **No guaranteed match**: Reverse image search may return zero results for
  images not indexed by Google.
- **Visual match ≠ identity match**: Google Lens returns visually similar
  images. A search result does not prove the person's identity.
- **Result quality varies**: Results depend on how widely the image appears
  on the public web.
- **No CAPTCHA bypass**: The system does not circumvent any platform
  protections.

## Blockchain

- **Testnet only**: Default deployment uses Sepolia testnet (no real value).
- **Confirmation latency**: Blockchain transactions take 15–60 seconds to
  confirm. This is inherent to the network.
- **Gas costs**: Each registration costs Sepolia ETH (free from faucets).
- **Immutability**: Once registered, records cannot be deleted or modified.
- **Not a proof of identity**: The blockchain proves data integrity, not
  that a person is who they claim to be.

## Privacy

- **Public data only**: The system only processes publicly accessible content.
- **No covert surveillance**: This is a demonstration system, not a
  surveillance tool.
- **Temporary image processing**: Uploaded images are processed in memory
  and not stored permanently.
- **On-chain data**: Only SHA-256 hashes and source URLs are stored on-chain.
  No personal data or face embeddings are recorded.

## General

- **Network dependency**: The system requires internet access for SerpAPI
  and blockchain operations.
- **No offline mode**: All external services must be reachable.
- **Single-user demo**: No authentication, multi-tenancy, or user management.
