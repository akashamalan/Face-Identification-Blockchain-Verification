# API Documentation

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs` (Swagger UI)
Alternative docs: `http://localhost:8000/redoc`

## Endpoints

### Health

#### GET /api/health
Returns service health status.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "services": {
    "face_engine": "ready",
    "search_provider": "configured",
    "blockchain": "connected"
  }
}
```

#### GET /api/preflight
Detailed configuration checks.

---

### Face

#### POST /api/face/detect
Detect faces in an uploaded image.

**Request:** multipart/form-data with `file` field
**Response:**
```json
{
  "success": true,
  "data": {
    "face_detected": true,
    "face_count": 1,
    "embedding_generated": false,
    "confidence": 0.95,
    "processing_time_ms": 342
  }
}
```

#### POST /api/face/encode
Detect one face and generate its embedding (embedding not returned).

---

### Search

#### POST /api/search/reverse-image
Perform reverse-image search.

**Request:** multipart/form-data with `file` field
**Response:**
```json
{
  "success": true,
  "data": {
    "provider": "SerpApiSearchProvider",
    "results_found": 5,
    "results": [...],
    "selected_result": { "title": "...", "url": "...", ... },
    "search_time_ms": 2100
  }
}
```

---

### Blockchain

#### POST /api/blockchain/register
Register a fingerprint on the blockchain.

**Request:**
```json
{
  "fingerprint": "abc123...64chars",
  "source_url": "https://example.com"
}
```

#### GET /api/blockchain/record/{record_id}
Retrieve a blockchain record.

#### POST /api/blockchain/verify
Verify post data against on-chain record.

---

### Pipeline

#### POST /api/pipeline/run
Execute the complete verification pipeline.

**Request:** multipart/form-data with `file` field (image with a face)

**Response:**
```json
{
  "success": true,
  "data": {
    "pipeline_id": "abc123",
    "status": "success",
    "face": { "face_detected": true, "face_count": 1 },
    "search": { "provider": "SerpApiSearchProvider", "results_found": 5 },
    "fingerprint": { "algorithm": "SHA-256", "value": "abc..." },
    "blockchain": { "network": "sepolia", "transaction_hash": "0x..." },
    "verification": { "status": "VERIFIED", "verified": true },
    "total_time_ms": 15000
  }
}
```

---

## Error Response Format

All errors follow this structure:
```json
{
  "success": false,
  "error": {
    "code": "FACE_NOT_FOUND",
    "message": "No face was detected in the uploaded image."
  }
}
```

### Error Codes
| Code | Description |
|------|-------------|
| `INVALID_IMAGE` | Invalid file type, empty, or too large |
| `FACE_NOT_FOUND` | No face detected |
| `MULTIPLE_FACES` | More than one face when one expected |
| `FACE_DETECTION_FAILED` | Face engine error |
| `SEARCH_NOT_CONFIGURED` | Missing API key |
| `SEARCH_ERROR` | Search provider failure |
| `SEARCH_TIMEOUT` | Search request timed out |
| `NO_SEARCH_RESULTS` | No matching results found |
| `BLOCKCHAIN_ERROR` | Blockchain transaction failure |
| `BLOCKCHAIN_NOT_CONFIGURED` | Missing blockchain credentials |
| `RECORD_NOT_FOUND` | Blockchain record not found |
| `VERIFICATION_ERROR` | Verification process failure |
