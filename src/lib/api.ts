export type AnalyzeMode = "greenfield" | "brownfield";

export interface GraphNode {
  id: string;
  label: string;
  type?: string | null;
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

export interface AnalyzeResponse {
  mode: AnalyzeMode;
  analysis_report: string;
  architecture_plan: string;
  ast_summary: string;
  graph: GraphPayload;
  memory_used: string;
  warning: string;
}

export interface AnalyzeRequest {
  mode: AnalyzeMode;
  input: string;
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
  if (!res.ok) {
    const text = await res.text();
    throw Object.assign(new Error(text || `Request failed: ${res.status}`), {
      status: res.status,
      body: text,
    });
  }
  return (await res.json()) as AnalyzeResponse;
}

async function analyzeViaPlannerGreenfield(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const payload: PlannerGreenfieldRequest = { description: req.input };
  const res = await fetch(`${API_BASE}/greenfield`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }

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

