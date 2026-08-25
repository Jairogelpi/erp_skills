import type {
  ApprovalGrant,
  AuditComparison,
  DemoRun,
  Evidence,
  ParaphraseResult,
  Preset,
  Timeline,
} from "../types/demo";

/**
 * Every call goes through the demo API. Nothing in the UI computes a
 * statistic or carries a fallback figure: if the evidence endpoint is
 * unavailable the panel says so, because rendering a placeholder number
 * would put a fabricated claim on screen.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${path}: ${detail}`);
  }
  return (await response.json()) as T;
}

export const api = {
  presets: () => request<Preset[]>("/demo/presets"),

  evidence: () => request<Evidence>("/demo/evidence"),

  run: (scenario: string, requestText?: string) =>
    request<DemoRun>("/demo/run", {
      method: "POST",
      body: JSON.stringify({
        scenario,
        request: requestText ?? null,
        backend: "fake",
      }),
    }),

  approve: (requestId: string, actor: string) =>
    request<ApprovalGrant>(`/demo/approval/${requestId}`, {
      method: "POST",
      body: JSON.stringify({ actor }),
    }),

  rerun: (requestId: string) =>
    request<DemoRun>(`/demo/rerun/${requestId}`, { method: "POST" }),

  audit: (requestId: string) =>
    request<AuditComparison>(`/demo/audit/${requestId}`),

  paraphrases: (requestId: string) =>
    request<ParaphraseResult>(`/demo/paraphrases/${requestId}`, {
      method: "POST",
    }),

  timeline: (requestId: string) => request<Timeline>(`/demo/timeline/${requestId}`),
};
