const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Auth helpers ──────────────────────────────────────────────────────────────

export function getToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

export function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface UserOut {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  allowed_collections: string[];
  is_active: boolean;
}

export async function login(email: string, password: string): Promise<UserOut> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Identifiants invalides");
  }
  const { access_token, refresh_token } = await res.json();
  setTokens(access_token, refresh_token);
  return fetchMe();
}

export async function fetchMe(): Promise<UserOut> {
  const res = await fetch(`${API_URL}/api/auth/me`, {
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  if (!res.ok) throw new Error("Non authentifié");
  return res.json();
}

export async function logout(): Promise<void> {
  clearTokens();
}

export interface SourceDoc {
  id: string;
  title: string | null;
  source_type: string;
  source_id: string;
  content_excerpt: string;
  score: number;
  url: string | null;
}

export interface StreamChunk {
  type: "token" | "sources" | "done" | "error";
  content?: string;
  sources?: SourceDoc[];
  query_log_id?: string;
}

export async function* streamQuery(
  question: string,
  collection = "general"
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ question, collection, stream: true }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Erreur API: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const chunk: StreamChunk = JSON.parse(line.slice(6));
          yield chunk;
        } catch {
          // Malformed SSE line — skip
        }
      }
    }
  }
}

export async function submitFeedback(
  queryLogId: string,
  feedback: 1 | -1
): Promise<void> {
  await fetch(`${API_URL}/api/query/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ query_log_id: queryLogId, feedback }),
  });
}

export async function ingestPDF(file: File, collection = "general"): Promise<{ job_id: string; message: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("collection", collection);

  const response = await fetch(`${API_URL}/api/ingest/pdf`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: form,
  });

  if (!response.ok) throw new Error(`Erreur ingestion: ${response.status}`);
  return response.json();
}
