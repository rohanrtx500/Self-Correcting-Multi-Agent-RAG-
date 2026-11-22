export interface QueryResponse {
  question: string;
  answer: string;
  sources: string[];
  steps: string[];
  execution_time: Record<string, number>;
  search_required: boolean;
  retry_count: number;
  retrieved_chunks?: Array<{ page_content: string; metadata?: Record<string, any> }>;
  web_results?: Array<{ title?: string; url?: string; content?: string }>;
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

export interface DocumentItem {
  title: string;
  source: string;
  chunk_count: number;
  preview: string;
}

export interface KnowledgeBaseResponse {
  total_chunks: number;
  total_documents: number;
  collection_name: string;
  documents: DocumentItem[];
}

export interface DocumentDeleteResponse {
  success: boolean;
  message: string;
  deleted_chunks: number;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function wrapNetworkError(err: unknown, endpoint: string): never {
  const errMsg = err instanceof Error ? err.message : String(err);
  if (errMsg.toLowerCase().includes("failed to fetch") || errMsg.toLowerCase().includes("networkerror")) {
    throw new Error(
      `Unable to reach backend at "${BACKEND_URL}${endpoint}". If using Render, the backend service may be waking from sleep (please retry in 30 seconds), or ensure NEXT_PUBLIC_API_URL is configured in Vercel settings.`
    );
  }
  if (err instanceof Error) {
    throw err;
  }
  throw new Error(String(err));
}

/**
 * Sends a query to the agentic self-correcting RAG pipeline.
 */
export async function sendQuery(question: string): Promise<QueryResponse> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });
  } catch (err: unknown) {
    wrapNetworkError(err, "/query");
  }

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
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/ingest`, {
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
  } catch (err: unknown) {
    wrapNetworkError(err, "/ingest");
  }

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

  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/upload`, {
      method: "POST",
      body: formData,
    });
  } catch (err: unknown) {
    wrapNetworkError(err, "/upload");
  }

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
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/health`, {
      cache: "no-store",
    });
  } catch (err: unknown) {
    wrapNetworkError(err, "/health");
  }

  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Fetches metrics logs.
 */
export async function getMetrics(): Promise<MetricsPayload> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/metrics`, {
      cache: "no-store",
    });
  } catch (err: unknown) {
    wrapNetworkError(err, "/metrics");
  }

  if (!res.ok) {
    throw new Error(`Failed to fetch metrics: ${res.status}`);
  }

  return res.json();
}

/**
 * Fetches the list of all documents and chunks in the Knowledge Base.
 */
export async function getKnowledgeBase(): Promise<KnowledgeBaseResponse> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/api/v1/documents`, {
      cache: "no-store",
    });
  } catch (err: unknown) {
    wrapNetworkError(err, "/api/v1/documents");
  }

  if (!res.ok) {
    throw new Error(`Failed to fetch knowledge base: ${res.status}`);
  }

  return res.json();
}

/**
 * Deletes a document from the Knowledge Base by title or source.
 */
export async function deleteDocument(identifier: string): Promise<DocumentDeleteResponse> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/api/v1/documents/${encodeURIComponent(identifier)}`, {
      method: "DELETE",
    });
  } catch (err: unknown) {
    wrapNetworkError(err, `/api/v1/documents/${identifier}`);
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete document: ${res.status}`);
  }

  return res.json();
}
