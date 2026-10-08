import { AdvisoryExplanationResult, Artifact, ArtifactVerifyResult, AuditLogItem, CrossSeedResult, Experiment, ParetoFrontierResult, Run, RunDiffResult, SensitivityResult, UserProfile } from "../types";

let cachedCsrfToken: string | null = null;
export function setCsrfToken(t: string | null) { cachedCsrfToken = t; }

let apiBaseUrl = "";
export function setBaseUrl(url: string) { apiBaseUrl = url; }

async function getCsrfToken(): Promise<string> {
  if (cachedCsrfToken) return cachedCsrfToken;
  try {
    const res = await fetch(`${apiBaseUrl}/api/v1/auth/csrf-token`, { credentials: "include" });
    if (res.ok) cachedCsrfToken = (await res.json()).csrf_token || "";
  } catch {}
  return cachedCsrfToken || "";
}

async function req<T>(path: string, opt: RequestInit = {}): Promise<T> {
  const method = (opt.method || "GET").toUpperCase();
  const headers = new Headers(opt.headers || {});
  if (!headers.has("Content-Type") && !(opt.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
    const csrf = await getCsrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  const res = await fetch(`${apiBaseUrl}${path}`, { ...opt, headers, credentials: "include" });
  if (res.status === 204) return null as unknown as T;
  if (!res.ok) {
    let msg = `Request failed: ${res.status}`;
    try { const j = await res.json(); if (j.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  auth: {
    getMe: () => req<UserProfile>("/api/v1/auth/me"),
    fetchCsrfToken: getCsrfToken,
    logout: () => req<{ status: string }>("/api/v1/auth/logout", { method: "POST" }),
    demoSwitch: async (profile: "admin" | "analyst" | "viewer") => {
      const d = await req<{ status: string; user: UserProfile; csrf_token: string }>("/api/v1/auth/demo-switch", { method: "POST", body: JSON.stringify({ profile }) });
      if (d.csrf_token) setCsrfToken(d.csrf_token);
      return d;
    },
  },
  experiments: {
    list: (p = 1, sz = 50, q = "") => req<{ items: Experiment[]; total: number; page: number; pages: number }>(`/api/v1/experiments?page=${p}&page_size=${sz}${q ? `&search=${encodeURIComponent(q)}` : ""}`),
    create: (data: any) => req<Experiment>("/api/v1/experiments", { method: "POST", body: JSON.stringify(data) }),
    delete: (id: string) => req<void>(`/api/v1/experiments/${id}`, { method: "DELETE" }),
  },
  runs: {
    list: (id: string, p = 1, sz = 100, variant?: string) => req<{ items: Run[]; total: number; page: number; pages: number }>(`/api/v1/runs?experiment_id=${id}&page=${p}&page_size=${sz}${variant ? `&variant_name=${encodeURIComponent(variant)}` : ""}`),
    create: (data: any) => req<Run>("/api/v1/runs", { method: "POST", body: JSON.stringify(data) }),
    delete: (id: string) => req<void>(`/api/v1/runs/${id}`, { method: "DELETE" }),
    diff: (b: string, t: string) => req<RunDiffResult>(`/api/v1/runs/diff?base_run_id=${b}&target_run_id=${t}`),
  },
  artifacts: {
    list: (id: string) => req<Artifact[]>(`/api/v1/runs/${id}/artifacts`),
    create: (id: string, data: any) => req<Artifact>(`/api/v1/runs/${id}/artifacts`, { method: "POST", body: JSON.stringify(data) }),
    verify: (id: string) => req<ArtifactVerifyResult>(`/api/v1/artifacts/${id}/verify`, { method: "POST" }),
  },
  analysis: {
    pareto: (experiment_id: string, objectives: any) => req<ParetoFrontierResult>("/api/v1/analysis/pareto", { method: "POST", body: JSON.stringify({ experiment_id, objectives }) }),
    crossSeed: (experiment_id: string, metrics: string[], baseline_variant?: string) => req<CrossSeedResult>("/api/v1/analysis/cross-seed", { method: "POST", body: JSON.stringify({ experiment_id, metrics, baseline_variant }) }),
    sensitivity: (experiment_id: string, target_metric: string) => req<SensitivityResult>("/api/v1/analysis/sensitivity", { method: "POST", body: JSON.stringify({ experiment_id, target_metric }) }),
    advisory: (experiment_id: string, analysis_type = "comprehensive") => req<AdvisoryExplanationResult>("/api/v1/analysis/advisory-explanation", { method: "POST", body: JSON.stringify({ experiment_id, analysis_type }) }),
  },
  audit: {
    list: (p = 1, sz = 50) => req<{ items: AuditLogItem[]; total: number; page: number; pages: number }>(`/api/v1/audit-logs?page=${p}&page_size=${sz}`),
  },
  bundles: {
    export: (id: string) => req<any>(`/api/v1/export/experiments/${id}`),
    exportReport: (id: string) => `/api/v1/export/experiments/${id}/report.md`,
    import: (bundle: any) => req<{ status: string; experiment: Experiment; runs_imported: number; artifacts_imported: number }>("/api/v1/import", { method: "POST", body: JSON.stringify({ bundle }) }),
  },
};

