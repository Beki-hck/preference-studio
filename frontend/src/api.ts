import type { Assignment, Project, ProjectStats, Rater, Side } from "./types";

const RATER_KEY = "prefstudio.rater";

export function savedRater(): Rater | null {
  try {
    const raw = localStorage.getItem(RATER_KEY);
    return raw ? (JSON.parse(raw) as Rater) : null;
  } catch {
    return null;
  }
}

export function saveRater(r: Rater | null) {
  try {
    if (r) localStorage.setItem(RATER_KEY, JSON.stringify(r));
    else localStorage.removeItem(RATER_KEY);
  } catch {
    /* storage unavailable: stay signed in for this page only */
  }
}

async function request<T>(path: string, init: RequestInit = {}, rater?: Rater | null): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (rater) headers["X-Rater-Id"] = String(rater.id);
  const res = await fetch(`/api${path}`, { ...init, headers: { ...headers, ...(init.headers as object) } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  signIn: (name: string) => request<Rater>("/raters", { method: "POST", body: JSON.stringify({ name }) }),
  projects: () => request<Project[]>("/projects"),
  project: (id: number) => request<Project>(`/projects/${id}`),
  createProject: (body: { name: string; description: string; overlap: number }) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify(body) }),
  createSample: () => request<Project>("/projects/sample", { method: "POST" }),
  importPairs: (id: number, jsonl: string) =>
    request<{ imported: number }>(`/projects/${id}/import`, { method: "POST", body: JSON.stringify({ jsonl }) }),
  next: (id: number, rater: Rater) => request<Assignment | null>(`/projects/${id}/next`, {}, rater),
  submit: (
    id: number,
    rater: Rater,
    body: { item_id: number; swapped: boolean; score: number; criteria: Record<string, Side>; rationale: string; seconds: number },
  ) => request<{ id: number }>(`/projects/${id}/labels`, { method: "POST", body: JSON.stringify(body) }, rater),
  stats: (id: number) => request<ProjectStats>(`/projects/${id}/stats`),
};

export function exportUrl(id: number, kind: "dpo" | "labels", params: Record<string, string | number | boolean> = {}) {
  const q = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
  const qs = q.toString();
  return `/api/projects/${id}/export/${kind}${qs ? `?${qs}` : ""}`;
}
