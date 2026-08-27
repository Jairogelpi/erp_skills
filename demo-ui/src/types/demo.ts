export type SystemName = "A" | "B" | "C";

export interface FieldChange {
  record: string;
  field: string;
  before: unknown;
  after: unknown;
}

export interface ErpDelta {
  before: Record<string, Record<string, Record<string, unknown>>>;
  after: Record<string, Record<string, Record<string, unknown>>>;
  changed: boolean;
  summary: string;
  created_ids: string[];
  field_changes: FieldChange[];
}

export interface AuditFacts {
  facts: Record<string, boolean>;
  coverage: number;
}

export interface DemoSystemResult {
  system: SystemName;
  label: string;
  intent: string | null;
  selected_capability: string | null;
  skill_version: string | null;
  arguments: Record<string, unknown>;
  retrieval_confidence: number | null;
  risk_class: string | null;
  policy_decision: string | null;
  policy_reasons: string[];
  findings: string[];
  approval_required: boolean | null;
  approval_status: string | null;
  execution_status: string;
  handler: string | null;
  error: string | null;
  erp: ErpDelta;
  postcondition_verified: boolean | null;
  postcondition_detail: string[];
  tokens: number | null;
  audit_id: string | null;
  audit: AuditFacts;
  unavailable: string[];
}

export interface DemoRun {
  request_id: string;
  scenario: string;
  request_text: string;
  backend: string;
  systems: Record<SystemName, DemoSystemResult>;
  approval_granted: boolean;
}

export interface Preset {
  id: string;
  label: string;
  request_text: string;
  description: string;
}

export interface ApprovalGrant {
  request_id: string;
  actor: string;
  scope: string;
  granted_at: string;
  expires_at: string;
}

/**
 * One hypothesis exactly as the frozen report states it. Every numeric
 * field here is loaded from the artifact by the API; none of it is
 * written in this codebase.
 */
export interface HypothesisCard {
  key: string;
  title: string;
  question: string;
  supported: boolean;
  verdict: string;
  evidence_state: string;
  estimate: number | null;
  estimate_kind: "percentage_points" | "tokens" | "proportion";
  effect_size: number | null;
  effect_size_name: string | null;
  n: number | null;
  test: string | null;
  criterion: string | null;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  population: string | null;
  unit: string | null;
}

export interface CapabilityRow {
  dimension: string;
  system_a: string;
  system_b: string;
  system_c: string;
  source_hypothesis: string | null;
}

export interface ConfinementArm {
  n: number;
  unauthorized_mutations: number;
  decisions: Record<string, number>;
}

export interface Confinement {
  total_attempts?: number;
  unauthorized_mutations?: number;
  payloads?: number;
  question?: string;
  arms?: Record<string, ConfinementArm>;
  source?: string;
}

export interface Evidence {
  protocol_tag: string;
  protocol_version: string;
  frozen_commit: string;
  frozen_at: string;
  campaign_state: string;
  observation_count: number;
  archive_hash: string;
  cards: HypothesisCard[];
  capability_matrix: CapabilityRow[];
  confinement: Confinement;
  disclaimer: string;
}

export interface AuditComparison {
  request_id: string;
  fact_names: string[];
  rows: Record<SystemName, Record<string, boolean>>;
  coverage: Record<SystemName, number>;
}

export interface ParaphraseRow {
  system: SystemName;
  outcomes: string[];
  capabilities: (string | null)[];
  consistent: boolean;
}

export interface ParaphraseResult {
  request_id: string;
  variants: string[];
  rows: ParaphraseRow[];
  disclaimer: string;
}

export interface TimelineEvent {
  at: string;
  label: string;
  detail: string | null;
}

export interface Timeline {
  request_id: string;
  events: TimelineEvent[];
}

// --- Product mode: Skills Catalog, Skill Studio, Operations, ------------
// --- unified Approvals/Audit (SPEC v2). ----------------------------------

export interface SkillView {
  skill_id: string;
  version: string;
  versions: string[];
  state: string;
  description: string;
  module: string;
  operation: string;
  risk_class: string;
  allowed_roles: string[];
  input_schema: Record<string, unknown>;
  preconditions: string[];
  postconditions: string[];
  handler: string;
  idempotent: boolean;
  approval_required_when: string[];
  odoo_wired: boolean;
}

export interface SkillHistoryEntry {
  from: string;
  to: string;
  actor: string;
  reason: string;
  recorded_at: string;
}

export interface SkillDetailView extends SkillView {
  history: SkillHistoryEntry[];
}

export interface DiffEntry {
  field: string;
  before: unknown;
  after: unknown;
}

export interface DraftResponse {
  contract: Record<string, unknown>;
  sample_arguments: Record<string, unknown>;
}

export interface ModifyResponse {
  contract: Record<string, unknown>;
  diff: DiffEntry[];
  sample_arguments: Record<string, unknown>;
}

export interface SandboxPreview {
  passed: boolean;
  detail: string;
  created_record: Record<string, unknown> | null;
}

export interface ProposalDescription {
  skill_id: string;
  version: string;
  description: string;
  risk_class: string;
  state: string;
  input_schema: Record<string, unknown>;
  history: SkillHistoryEntry[];
  sandbox_preview?: SandboxPreview;
}

export interface OperationCandidate {
  skill_id: string;
  score: number;
}

export interface OperationExecution {
  output: unknown;
  idempotent_replay: boolean;
  handler_error: string | null;
}

export interface OperationResult {
  correlation_id: string;
  decision: string;
  selected_skill_id?: string | null;
  reasons: string[];
  candidates: OperationCandidate[];
  extracted_arguments?: Record<string, unknown>;
  note?: string;
  execution?: OperationExecution;
  independent_reread?: Record<string, unknown>;
}

export interface ApprovalRow {
  kind: "erp_execution" | "skill_activation";
  actor: string;
  scope: string;
  granted_at: string;
  expires_at?: string;
  to_state?: string;
}

export interface AuditRow {
  kind: "erp_request" | "skill_evolution";
  correlation_id?: string;
  skill_id?: string;
  version?: string;
  decision?: string;
  risk_score?: number;
  reasons?: string[];
  from_state?: string;
  to_state?: string;
  actor?: string;
  reason?: string;
  recorded_at: string;
}

export interface ApprovalEvaluation {
  requires_approval: boolean;
  matched_conditions: string[];
  unparsed_conditions: string[];
}
