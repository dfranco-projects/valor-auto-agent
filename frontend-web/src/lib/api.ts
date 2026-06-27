// typed client for the valor-auto-agent FastAPI backend. mirrors src/frontend/api.py.
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Role = "user" | "assistant" | "error";
export type Filters = Record<string, string | number | null>;

export interface SearchResult {
  score: number;
  rationale: string;
  title: string | null;
  price_eur: number | null;
  year: number | null;
  km: number | null;
  source: string;
  external_id?: string;
  url: string;
  status?: string | null;
  also_on?: { source: string; url: string }[];
}

export interface SearchResponse {
  status: "need_filters" | "done";
  reply: string | null;
  top: SearchResult[];
  filter_schema: Record<string, unknown> | null;
  prefill: Filters;
}

export interface SessionOut {
  thread_id: string;
  history: [Role, string][];
  top: SearchResult[];
  rater_model: string | null;
}

export interface SessionMeta {
  thread_id: string;
  title: string;
  updated_at: string | null;
}

export interface ConfigOut {
  models: string[];
  default_model: string;
  anthropic_key: boolean;
  gemini_key: boolean;
}

export interface Evaluation {
  source: string;
  external_id: string;
  brand: string | null;
  model: string | null;
  title: string;
  year: number | null;
  km: number | null;
  price_eur: number | null;
  fuel: string | null;
  transmission: string | null;
  location: string | null;
  score: number;
  rationale: string;
  rated_by: string;
  rated_at: string | null;
  status: string | null;
  notes: string;
  url: string;
}

export interface SavedSearch {
  id: number;
  name: string;
  filters: Filters;
  cadence_minutes: number;
  active: boolean;
  last_run_at: string | null;
  new_count: number;
}

export interface Alert {
  id: number;
  saved_search_id: number;
  source: string;
  external_id: string;
  title: string;
  price_eur: number | null;
  year: number | null;
  km: number | null;
  url: string;
  score: number | null;
  rationale: string;
  read: boolean;
  created_at: string | null;
}

export class ApiError extends Error {}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = (await res.text()).slice(0, 300) || res.statusText;
    throw new ApiError(`backend error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getConfig: () => call<ConfigOut>("GET", "/api/config"),
  patchConfig: (rater_model: string) =>
    call<ConfigOut>("PATCH", "/api/config", { rater_model }),
  getActiveSession: () => call<SessionOut>("GET", "/api/sessions/active"),
  getSessions: () => call<SessionMeta[]>("GET", "/api/sessions"),
  getSession: (threadId: string) => call<SessionOut>("GET", `/api/sessions/${threadId}`),
  newSession: () => call<SessionOut>("POST", "/api/sessions/new"),
  postSearch: (threadId: string, message: string, raterModel: string | null) =>
    call<SearchResponse>("POST", "/api/search", {
      thread_id: threadId,
      message,
      rater_model: raterModel,
    }),
  postResume: (threadId: string, filters: Filters) =>
    call<SearchResponse>("POST", "/api/search/resume", { thread_id: threadId, filters }),
  getEvaluations: (params: {
    search?: string;
    sources?: string[];
    min_score?: number;
    statuses?: string[];
  } = {}) => {
    const q = new URLSearchParams();
    if (params.search) q.set("search", params.search);
    (params.sources ?? []).forEach((s) => q.append("sources", s));
    if (params.min_score != null) q.set("min_score", String(params.min_score));
    (params.statuses ?? []).forEach((s) => q.append("statuses", s));
    const qs = q.toString();
    return call<Evaluation[]>("GET", `/api/evaluations${qs ? `?${qs}` : ""}`);
  },
  patchDecision: (source: string, externalId: string, status: string | null, notes: string) =>
    call<{ ok: boolean }>("PATCH", "/api/evaluations", {
      source,
      external_id: externalId,
      status,
      notes,
    }),
  getSaved: () => call<SavedSearch[]>("GET", "/api/saved-searches"),
  createSaved: (name: string, filters: Filters, cadence_minutes: number) =>
    call<SavedSearch>("POST", "/api/saved-searches", { name, filters, cadence_minutes }),
  deleteSaved: (id: number) => call<{ ok: boolean }>("DELETE", `/api/saved-searches/${id}`),
  runSaved: (id: number) => call<Alert[]>("POST", `/api/saved-searches/${id}/run`),
  getAlerts: (unreadOnly = false) =>
    call<Alert[]>("GET", `/api/alerts${unreadOnly ? "?unread_only=true" : ""}`),
  readAlert: (id: number) => call<{ ok: boolean }>("POST", `/api/alerts/${id}/read`),
};
