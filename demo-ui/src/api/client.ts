import type {
  ApprovalEvaluation,
  ApprovalGrant,
  ApprovalRow,
  AuditComparison,
  AuditRow,
  DemoRun,
  DraftResponse,
  Evidence,
  ModifyResponse,
  OperationResult,
  ParaphraseResult,
  Preset,
  ProposalDescription,
  SkillDetailView,
  SkillView,
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

  // --- Product mode ------------------------------------------------------

  skills: () => request<SkillView[]>("/product/skills"),

  skillDetail: (skillId: string) =>
    request<SkillDetailView>(`/product/skills/${encodeURIComponent(skillId)}`),

  quarantineSkill: (skillId: string, actor: string, reason: string) =>
    request<SkillDetailView>(
      `/product/skills/${encodeURIComponent(skillId)}/quarantine`,
      { method: "POST", body: JSON.stringify({ actor, reason }) },
    ),

  deprecateSkill: (skillId: string, actor: string) =>
    request<SkillDetailView>(
      `/product/skills/${encodeURIComponent(skillId)}/deprecate`,
      { method: "POST", body: JSON.stringify({ actor }) },
    ),

  draftSkill: (description: string) =>
    request<DraftResponse>("/product/skill-studio/draft", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),

  modifySkill: (contract: Record<string, unknown>, instruction: string) =>
    request<ModifyResponse>("/product/skill-studio/modify", {
      method: "POST",
      body: JSON.stringify({ contract, instruction }),
    }),

  testProposal: (
    contract: Record<string, unknown>,
    sampleArguments?: Record<string, unknown>,
  ) =>
    request<ProposalDescription>("/product/skill-studio/test", {
      method: "POST",
      body: JSON.stringify({ contract, sample_arguments: sampleArguments ?? null }),
    }),

  approveProposal: (skillId: string, version: string, approver: string) =>
    request<ProposalDescription>("/product/skill-studio/approve", {
      method: "POST",
      body: JSON.stringify({ skill_id: skillId, version, approver }),
    }),

  proposals: () => request<ProposalDescription[]>("/product/skill-studio/proposals"),

  runOperation: (text: string, role = "erp_user") =>
    request<OperationResult>("/product/operations/run", {
      method: "POST",
      body: JSON.stringify({ text, role }),
    }),

  grantExecutionApproval: (scope: string, ttlSeconds = 120) =>
    request<ApprovalRow>("/product/approvals", {
      method: "POST",
      body: JSON.stringify({ scope, ttl_seconds: ttlSeconds }),
    }),

  productApprovals: () => request<ApprovalRow[]>("/product/approvals"),

  productAudit: () => request<AuditRow[]>("/product/audit"),

  evaluateApproval: (conditions: string[], affectedCount: number) =>
    request<ApprovalEvaluation>("/product/skill-studio/evaluate-approval", {
      method: "POST",
      body: JSON.stringify({ conditions, affected_count: affectedCount }),
    }),
};
