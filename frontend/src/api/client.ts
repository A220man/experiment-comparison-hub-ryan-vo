import { AdvisoryExplanationResult, Artifact, ArtifactVerifyResult, AuditLogItem, CrossSeedResult, Experiment, LeaderboardResult, ObjectiveConfig, ParetoFrontierResult, Run, RunDiffResult, SensitivityResult, TuningRecommendationsResponse, UserProfile } from "../types";

let cachedCsrfToken: string | null = null, apiBaseUrl = "";
export const setCsrfToken = (t: string | null) => { cachedCsrfToken = t; };
export const setBaseUrl = (url: string) => { apiBaseUrl = url; };

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

const v1 = "/api/v1";
type Pag<T> = { items: T[]; total: number; page: number; pages: number };
const pJ = <T>(p: string, b: any, m = "POST") => req<T>(p, { method: m, body: JSON.stringify(b) });
const del = (p: string) => req<void>(p, { method: "DELETE" });

export const api = {
  auth: {
    getMe: () => req<UserProfile>(`${v1}/auth/me`),
    fetchCsrfToken: getCsrfToken,
    logout: () => pJ<{ status: string }>(`${v1}/auth/logout`, {}),
    demoSwitch: async (profile: "admin" | "analyst" | "viewer") => {
      const d = await pJ<{ status: string; user: UserProfile; csrf_token: string }>(`${v1}/auth/demo-switch`, { profile });
      if (d.csrf_token) setCsrfToken(d.csrf_token);
      return d;
    },
  },
  experiments: {
    list: (p = 1, sz = 50, q = "") => req<Pag<Experiment>>(`${v1}/experiments?page=${p}&page_size=${sz}${q ? `&search=${encodeURIComponent(q)}` : ""}`),
    create: (data: any) => pJ<Experiment>(`${v1}/experiments`, data),
    delete: (id: string) => del(`${v1}/experiments/${id}`),
  },
  runs: {
    list: (id: string, p = 1, sz = 100, v?: string) => req<Pag<Run>>(`${v1}/runs?experiment_id=${id}&page=${p}&page_size=${sz}${v ? `&variant_name=${encodeURIComponent(v)}` : ""}`),
    create: (data: any) => pJ<Run>(`${v1}/runs`, data),
    update: (id: string, data: any) => pJ<Run>(`${v1}/runs/${id}`, data, "PUT"),
    delete: (id: string) => del(`${v1}/runs/${id}`),
    diff: (b: string, t: string) => req<RunDiffResult>(`${v1}/runs/diff?base_run_id=${b}&target_run_id=${t}`),
  },
  artifacts: {
    list: (id: string) => req<Artifact[]>(`${v1}/runs/${id}/artifacts`),
    create: (id: string, data: any) => pJ<Artifact>(`${v1}/runs/${id}/artifacts`, data),
    verify: (id: string) => pJ<ArtifactVerifyResult>(`${v1}/artifacts/${id}/verify`, {}),
  },
  analysis: {
    pareto: (experiment_id: string, objectives: ObjectiveConfig[], opts: Record<string, unknown> = {}) => pJ<ParetoFrontierResult>(`${v1}/analysis/pareto`, { experiment_id, objectives, ...opts }),
    crossSeed: (experiment_id: string, metrics: string[], baseline_variant?: string) => pJ<CrossSeedResult>(`${v1}/analysis/cross-seed`, { experiment_id, metrics, baseline_variant }),
    sensitivity: (experiment_id: string, target_metric: string) => pJ<SensitivityResult>(`${v1}/analysis/sensitivity`, { experiment_id, target_metric }),
    advisory: (experiment_id: string, analysis_type = "comprehensive") => pJ<AdvisoryExplanationResult>(`${v1}/analysis/advisory-explanation`, { experiment_id, analysis_type }),
    leaderboard: (experiment_id: string, objectives: ObjectiveConfig[], opts: Record<string, unknown> = {}) => pJ<LeaderboardResult>(`${v1}/analysis/leaderboard`, { experiment_id, objectives, ...opts }),
  },
  tuning: {
    recommendations: (experiment_id: string, target_metric: string, objectives?: ObjectiveConfig[], variant_filter?: string[], seed_filter?: number[], aggregate_by_variant?: boolean, aggregation_method?: string) => 
      pJ<TuningRecommendationsResponse>(`${v1}/tuning/recommendations`, { 
        experiment_id, 
        target_metric, 
        objectives, 
        variant_filter, 
        seed_filter, 
        aggregate_by_variant, 
        aggregation_method 
      }),
  },
  audit: {
    list: (p = 1, sz = 50) => req<Pag<AuditLogItem>>(`${v1}/audit-logs?page=${p}&page_size=${sz}`),
  },
  bundles: {
    export: (id: string) => req<any>(`${v1}/export/experiments/${id}`),
    exportReport: (id: string) => `${v1}/export/experiments/${id}/report.md`,
    import: (bundle: any) => pJ<{ status: string; experiment: Experiment; runs_imported: number; artifacts_imported: number }>(`${v1}/import`, { bundle }),
  },
};
