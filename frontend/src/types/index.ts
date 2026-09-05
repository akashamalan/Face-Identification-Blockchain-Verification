export interface FaceData {
  face_detected: boolean;
  face_count: number;
  embedding_generated: boolean;
  bbox: number[];
  confidence: number;
  processing_time_ms: number;
  engine: string;
  det_score: number;
}

export interface SearchResult {
  title: string;
  url: string;
  domain: string;
  platform: string;
  snippet: string;
  image_url: string;
  thumbnail: string;
  metadata: Record<string, unknown>;
  similarity: number | null;
  match_reason: string;
}

export interface CandidateEvidence {
  position: number;
  url: string;
  domain: string;
  image_source: string;
  image_sha256: string;
  image_bytes: number;
  faces_detected: number;
  similarity: number | null;
  decision: "accepted" | "rejected_below_threshold" | "skipped" | string;
  reason: string;
}

export interface MatchingResult {
  status: "match" | "no_confident_match";
  threshold: number;
  candidates: CandidateEvidence[];
  selected_position: number | null;
  best_similarity: number | null;
  matched_image_sha256: string;
  audit_bundle_sha256: string;
  candidates_total: number;
  candidates_scored: number;
  candidates_skipped: number;
  matching_time_ms: number;
}

export interface SearchResponse {
  provider: string;
  results_found: number;
  results: SearchResult[];
  selected_result: SearchResult | null;
  search_time_ms: number;
}

export interface Fingerprint {
  algorithm: string;
  value: string;
  canonical_data: Record<string, unknown>;
}

export interface BlockchainRecord {
  network: string;
  transaction_hash: string;
  block_number: number;
  fingerprint: string;
  source_url: string;
  timestamp: number;
  submitter: string;
  explorer_url: string;
  submission_time_ms: number;
}

export interface VerificationResult {
  verified: boolean;
  status: "VERIFIED" | "TAMPERED" | "PENDING" | "ERROR";
  local_fingerprint: string;
  on_chain_fingerprint: string;
  record_id: string;
  transaction_hash: string;
  verification_time_ms: number;
}

export interface PipelineResult {
  pipeline_id: string;
  status: "success" | "error" | "pending" | "no_confident_match";
  face: FaceData;
  search: SearchResponse;
  matching: MatchingResult;
  fingerprint: Fingerprint;
  blockchain: BlockchainRecord;
  on_chain_record: BlockchainRecord;
  verification: VerificationResult;
  total_time_ms: number;
  error: string | null;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, string>;
}

export type StageStatus = "idle" | "running" | "success" | "error";

export interface PipelineStage {
  id: string;
  label: string;
  status: StageStatus;
  detail?: string;
}
