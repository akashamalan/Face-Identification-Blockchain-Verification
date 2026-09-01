export interface FaceData {
  face_detected: boolean;
  face_count: number;
  embedding_generated: boolean;
  bbox: number[];
  confidence: number;
  processing_time_ms: number;
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
  transaction_hash: string;
  verification_time_ms: number;
}

export interface PipelineResult {
  pipeline_id: string;
  status: "success" | "error" | "pending";
  face: FaceData;
  search: SearchResponse;
  fingerprint: Fingerprint;
  blockchain: BlockchainRecord;
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
