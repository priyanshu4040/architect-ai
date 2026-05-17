import {
  throwIfApiError,
  type ApiKeyStatusResponse,
  type ApiKeyValidateResponse,
} from "@/lib/apiErrors";

export type AnalyzeMode = "greenfield" | "brownfield";

export interface GraphNode {
  id: string;
  label: string;
  type?: string | null;
  layer?: "presentation" | "business" | "data" | "infrastructure" | null;
  functionality?: string | null;
  description?: string | null;
  group?: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  label?: string | null;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GreenfieldStructuredOutput {
  project_summary: string;
  detected_domain: string;
  assumptions?: string[];
  functional_requirements: string[];
  non_functional_requirements: string[];
  suggested_architecture: {
    frontend: string;
    backend: string;
    database: string;
    authentication: string;
    deployment: string;
  };
  modules: string[];
  api_suggestions: string[];
  database_entities: string[];
  security_suggestions: string[];
  scalability_suggestions: string[];
  architecture_flow: string[];
  final_summary: string;
}

export interface DetectedStack {
  frontend?: string;
  backend?: string;
  database?: string;
  authentication?: string;
  deployment?: string[];
  api_style?: string;
}

export interface FolderAnalysisItem {
  folder: string;
  purpose: string;
  quality: string;
  suggestion: string;
}

export interface DetectedModuleItem {
  name: string;
  type?: string;
  path?: string;
  evidence?: string;
  confidence?: string;
}

export interface SuggestedModuleItem {
  name: string;
  reason?: string;
  priority?: string;
}

export interface DetectedApiItem {
  method: string;
  path: string;
  file: string;
  purpose: string;
  evidence?: string;
}

export interface IssueItem {
  issue: string;
  severity: string;
  reason: string;
  suggested_fix: string;
  affected_area?: string;
  evidence?: string;
  affected_file_or_folder?: string;
}

export interface EvolutionPlan {
  immediate_fixes: string[];
  short_term_improvements: string[];
  long_term_improvements: string[];
}

export interface DetectedTechStackDetail {
  languages?: string[];
  language_percentages?: Record<string, number>;
  frameworks?: string[];
  libraries?: string[];
  databases?: string[];
  build_tools?: string[];
  deployment?: string[];
  package_managers?: string[];
  evidence?: Record<string, string[]>;
  confidence?: Record<string, string>;
  folder_structure?: string[];
  validation_message?: string;
}

export interface BrownfieldStructuredOutput {
  project_summary: string;
  detected_tech_stack?: DetectedTechStackDetail;
  detected_stack: DetectedStack | string[];
  folder_analysis: FolderAnalysisItem[] | string[];
  detected_modules: DetectedModuleItem[] | string[];
  suggested_modules?: SuggestedModuleItem[];
  detected_apis: DetectedApiItem[] | string[];
  architecture_issues: IssueItem[] | string[];
  security_issues: IssueItem[] | string[];
  scalability_issues: IssueItem[] | string[];
  maintainability_issues?: IssueItem[] | string[];
  improvement_suggestions: string[];
  evolution_plan: EvolutionPlan | string[];
  final_summary: string;
  is_fallback?: boolean;
  structured_partial?: boolean;
  fallback_type?: string;
  message?: string;
  fallback_reason?: string;
}

export interface RequirementsCompileResponse {
  requirement_source: string;
  project_type: string;
  users: string[];
  functional_requirements: string[];
  non_functional_requirements: string[];
  preferred_stack: string;
  project_level: string;
  deployment_preference: string;
  generated_requirement_summary: string;
}

export interface ModifyArchitectureResponse {
  updated_architecture: AnalyzeResponse;
  changes_applied: string[];
  reasoning: string[];
  impact_analysis: Record<string, string>;
  final_summary: string;
}

export interface ProjectTemplate {
  id: string;
  name: string;
}

export interface AnalyzeResponse {
  mode: AnalyzeMode;
  analysis_report: string;
  architecture_plan: string;
  ast_summary: string;
  graph: GraphPayload;
  memory_used: string;
  warning: string;
  results?: AnalyzeResults | null;
  structured_output?: GreenfieldStructuredOutput | BrownfieldStructuredOutput | null;
  report_document?: string;
  is_fallback?: boolean;
  structured_partial?: boolean;
  fallback_type?: string | null;
}

export type AnalyzeResults = {
  current_codebase_faults?: {
    fault: string;
    severity: "high" | "medium" | "low" | string;
    evidence: string;
    impact: string;
  }[];
  comparison_old_vs_new?: {
    dimension: string;
    current_state: string;
    proposed_state: string;
    benefit: string;
  }[];
  expected_improvements?: {
    metric: "maintainability" | "scalability" | "performance" | "security" | "delivery_speed" | string;
    current_baseline: string;
    target_outcome: string;
    why_it_improves: string;
  }[];
  component_details?: {
    component: string;
    functionality: string;
    inputs?: string[] | null;
    outputs?: string[] | null;
    dependencies?: string[] | null;
  }[];
  component_layer_mapping?: {
    component: string;
    layer: "presentation" | "business" | "data" | "infrastructure" | string;
    reason?: string;
    confidence?: number;
  }[];
  recommended_patterns?: {
    pattern: string;
    why: string;
    confidence: number;
    tags?: string[] | null;
  }[];
  key_decisions?: {
    decision: string;
    rationale: string;
    alternatives?: string[] | null;
  }[];
  risk_analysis?: {
    risk: string;
    severity: "high" | "medium" | "low" | string;
    impact: string;
    likelihood: "high" | "medium" | "low" | string;
    mitigation: string;
  }[];
  evolution_roadmap?: {
    phase: string;
    timeframe: string;
    goals?: string[] | null;
    deliverables?: string[] | null;
  }[];
  indicators?: {
    scalability: number;
    performance: number;
    maintainability: number;
    security: number;
    notes?: Partial<Record<"scalability" | "performance" | "maintainability" | "security", string>>;
  };
};

export interface AnalyzeRequest {
  mode: AnalyzeMode;
  input: string;
  project_name?: string | null;
  scalability?: number | null;
  performance?: number | null;
  maintainability?: number | null;
  security?: number | null;
  expected_users?: string | null;
  growth_rate?: string | null;
}

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE?.toString() ||
  "http://localhost:8000";

type PlannerGreenfieldRequest = {
  description: string;
  expected_users?: string | null;
  scalability?: string | null;
  complexity?: string | null;
  constraints?: string[] | null;
};

type PlannerSuggestion = {
  suggested_architecture: string;
  reason: string;
  pattern_description?: string | null;
  pros?: string[] | null;
  cons?: string[] | null;
};

type PlannerGreenfieldResponse = {
  analysis: { scalability: string; complexity: string };
  suggestion: PlannerSuggestion;
  agent_logs?: unknown[] | null;
};

async function analyzeViaApiAnalyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  await throwIfApiError(res);
  return (await res.json()) as AnalyzeResponse;
}

async function analyzeViaPlannerGreenfield(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const payload: PlannerGreenfieldRequest = { description: req.input };
  const res = await fetch(`${API_BASE}/greenfield`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await throwIfApiError(res);

  const data = (await res.json()) as PlannerGreenfieldResponse;
  const s = data.suggestion;
  const analysisLines = [
    `Scalability: ${data.analysis?.scalability ?? ""}`.trim(),
    `Complexity: ${data.analysis?.complexity ?? ""}`.trim(),
  ].filter(Boolean);

  const planLines = [
    `## Suggested Architecture`,
    s?.suggested_architecture ? `- ${s.suggested_architecture}` : "",
    "",
    `## Reason`,
    s?.reason || "",
    s?.pattern_description ? `\n## Pattern Description\n${s.pattern_description}` : "",
    s?.pros?.length ? `\n## Pros\n${s.pros.map((p) => `- ${p}`).join("\n")}` : "",
    s?.cons?.length ? `\n## Cons\n${s.cons.map((c) => `- ${c}`).join("\n")}` : "",
  ].filter(Boolean);

  return {
    mode: "greenfield",
    analysis_report: analysisLines.join("\n"),
    architecture_plan: planLines.join("\n"),
    ast_summary: "",
    graph: { nodes: [], edges: [] },
    memory_used: "",
    warning:
      "Using Web Architecture Planner compatibility mode (/greenfield). Start this repo backend to enable /api/analyze and richer outputs.",
  };
}

export async function analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  try {
    return await analyzeViaApiAnalyze(req);
  } catch (err: unknown) {
    const status = (err as any)?.status;
    if (status === 404 && req.mode === "greenfield") {
      return await analyzeViaPlannerGreenfield(req);
    }
    if (status === 404 && req.mode === "brownfield") {
      throw new Error(
        "Backend at VITE_API_BASE does not support /api/analyze. Start this repo backend with `python -m uvicorn app:app --reload --port 8000` (or set VITE_API_BASE to its port)."
      );
    }
    throw err;
  }
}

export async function analyzeBrownfieldZip(file: File): Promise<AnalyzeResponse> {
  const fd = new FormData();
  fd.append("file", file, file.name);

  const res = await fetch(`${API_BASE}/api/brownfield/zip`, {
    method: "POST",
    body: fd,
  });
  await throwIfApiError(res);
  return (await res.json()) as AnalyzeResponse;
}

export async function fetchApiKeyStatus(): Promise<ApiKeyStatusResponse> {
  const res = await fetch(`${API_BASE}/api/api-key/status`);
  await throwIfApiError(res);
  return (await res.json()) as ApiKeyStatusResponse;
}

export async function validateApiKey(apiKey?: string): Promise<ApiKeyValidateResponse> {
  const res = await fetch(`${API_BASE}/api/api-key/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(apiKey?.trim() ? { api_key: apiKey.trim() } : {}),
  });
  const data = (await res.json()) as ApiKeyValidateResponse;
  if (!res.ok && !data.message) {
    await throwIfApiError(res);
  }
  return data;
}

const LAST_RESULT_KEY = "architect_ai:last_result";

export function saveLastResult(result: AnalyzeResponse) {
  sessionStorage.setItem(LAST_RESULT_KEY, JSON.stringify(result));
}

export function loadLastResult(): AnalyzeResponse | null {
  const raw = sessionStorage.getItem(LAST_RESULT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AnalyzeResponse;
  } catch {
    return null;
  }
}

export function clearLastResult(): void {
  sessionStorage.removeItem(LAST_RESULT_KEY);
}

export interface NfrSuggestResponse {
  improved_prompt: string;
  suggestions: string[];
  reasoning: string;
}

export async function listTemplates(): Promise<ProjectTemplate[]> {
  const res = await fetch(`${API_BASE}/api/templates`);
  if (!res.ok) throw new Error("Failed to load templates");
  const data = (await res.json()) as { templates: ProjectTemplate[] };
  return data.templates;
}

export async function getTemplate(id: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/templates/${id}`);
  if (!res.ok) throw new Error("Template not found");
  return (await res.json()) as Record<string, unknown>;
}

export async function compileRequirements(body: {
  source: "guided" | "template";
  template_id?: string;
  answers?: Record<string, unknown>;
  overrides?: Record<string, unknown>;
}): Promise<RequirementsCompileResponse> {
  const res = await fetch(`${API_BASE}/api/requirements/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await throwIfApiError(res);
  return (await res.json()) as RequirementsCompileResponse;
}

export async function modifyArchitecture(body: {
  mode: AnalyzeMode;
  current_architecture: AnalyzeResponse;
  user_change_request: string;
}): Promise<ModifyArchitectureResponse> {
  const res = await fetch(`${API_BASE}/api/modify-architecture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await throwIfApiError(res);
  return (await res.json()) as ModifyArchitectureResponse;
}

const MOD_HISTORY_KEY = "architect_ai:mod_history";

export function appendModificationHistory(entry: {
  request: string;
  response: ModifyArchitectureResponse;
  at: string;
}) {
  const raw = sessionStorage.getItem(MOD_HISTORY_KEY);
  const list = raw ? (JSON.parse(raw) as unknown[]) : [];
  list.push(entry);
  sessionStorage.setItem(MOD_HISTORY_KEY, JSON.stringify(list.slice(-20)));
}

export function loadModificationHistory(): unknown[] {
  const raw = sessionStorage.getItem(MOD_HISTORY_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as unknown[];
  } catch {
    return [];
  }
}

export async function suggestNfr(params: {
  prompt: string;
  scalability: number;
  performance: number;
  maintainability: number;
  security: number;
}): Promise<NfrSuggestResponse> {
  const res = await fetch(`${API_BASE}/api/suggest-nfr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  await throwIfApiError(res);
  return (await res.json()) as NfrSuggestResponse;
}
