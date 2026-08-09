export interface QueryResponse {
  question: string;
  answer: string;
  sources: string[];
  steps: string[];
  execution_time: Record<string, number>;
  search_required: boolean;
  retry_count: number;
  retrieved_chunks?: Array<{ page_content: string; metadata?: Record<string, any> }>;
  errors: string[];
}

export interface IngestionResponse {
  success: boolean;
  message: string;
  chunks_count: number;
}

export interface HealthStatus {
  status: string;
  llm_provider: string;
  database_connected: boolean;
}

export interface MetricsPayload {
  uptime_seconds: number;
  queries_processed: number;
  average_query_latency: number;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Sends a query to the agentic self-correcting RAG pipeline.
 */
export async function sendQuery(question: string): Promise<QueryResponse> {
  const res = await fetch(`${BACKEND_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

/**
 * Triggers ingestion for a file or directory path.
 */
export async function triggerIngestion(
  path: string,
  chunkSize: number = 800,
  chunkOverlap: number = 150
): Promise<IngestionResponse> {
  const res = await fetch(`${BACKEND_URL}/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      path,
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

/**
 * Uploads a file document directly to the backend for ingestion.
 */
export async function uploadDocument(file: File): Promise<IngestionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BACKEND_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Checks backend health and connection to Chroma DB.
 */
export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BACKEND_URL}/health`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Fetches metrics logs.
 */
export async function getMetrics(): Promise<MetricsPayload> {
  const res = await fetch(`${BACKEND_URL}/metrics`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch metrics: ${res.status}`);
  }

  return res.json();
}
