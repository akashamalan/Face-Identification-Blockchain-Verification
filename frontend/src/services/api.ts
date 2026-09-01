import type { ApiResponse, HealthResponse, PipelineResult } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_URL}${path}`, options);
  const json = await res.json();
  return json as ApiResponse<T>;
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`);
  return res.json();
}

export async function checkPreflight() {
  const res = await fetch(`${API_URL}/preflight`);
  return res.json();
}

export async function runPipeline(
  file: File
): Promise<ApiResponse<PipelineResult>> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_URL}/pipeline/run`, {
    method: "POST",
    body: form,
  });
  return res.json();
}

export async function detectFace(file: File): Promise<ApiResponse<unknown>> {
  const form = new FormData();
  form.append("file", file);
  return request("/face/detect", { method: "POST", body: form });
}

export async function reverseImageSearch(
  file: File
): Promise<ApiResponse<unknown>> {
  const form = new FormData();
  form.append("file", file);
  return request("/search/reverse-image", { method: "POST", body: form });
}
