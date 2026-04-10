import { motion } from "framer-motion";
import { 
  AlertTriangle, 
  BarChart3, 
  CheckCircle2, 
  ChevronRight, 
  GitBranch, 
  Layers, 
  Shield, 
  TrendingUp,
  Zap
} from "lucide-react";
import { Link } from "react-router-dom";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { AnalyzeResults, loadLastResult } from "@/lib/api";

type Recommendation = {
  title: string;
  description: string;
  confidence: number;
  tags: string[];
};

type Decision = { decision: string; justification: string };
type Risk = {
  title: string;
  severity: "high" | "medium" | "low";
  description: string;
  mitigation: string;
};
type RoadmapPhase = { month: string; items: string[] };

function clamp01to100(n: number) {
  return Math.max(0, Math.min(100, Math.round(n)));
}

function takeBullets(text: string, limit: number): string[] {
  const lines = (text || "").split("\n").map((l) => l.trim());
  const bullets = lines
    .filter((l) => /^[-*]\s+/.test(l))
    .map((l) => l.replace(/^[-*]\s+/, "").trim())
    .filter(Boolean);
  return bullets.slice(0, limit);
}

function extractSection(text: string, headingLike: RegExp): string {
  const lines = (text || "").split("\n");
  const idx = lines.findIndex((l) => headingLike.test(l.trim()));
  if (idx < 0) return "";
  const out: string[] = [];
  for (let i = idx + 1; i < lines.length; i++) {
    const t = lines[i].trim();
    if (/^#{1,6}\s+/.test(t)) break;
    out.push(lines[i]);
  }
  return out.join("\n").trim();
}

function buildRecommendations(plan: string, report: string): Recommendation[] {
  const source = `${plan}\n\n${report}`;
  const picked: Recommendation[] = [];

  const keywords: { title: string; tags: string[]; descriptionHint: string; rx: RegExp }[] = [
    { title: "Microservices Architecture", tags: ["Scalable", "Independent Deployments"], descriptionHint: "Split core domains into independently deployable services.", rx: /\bmicroservices?\b/i },
    { title: "Modular Monolith", tags: ["Maintainable", "Clear Boundaries"], descriptionHint: "Start modular with strict boundaries; split later if needed.", rx: /\bmodular monolith\b/i },
    { title: "Layered Architecture", tags: ["Maintainable", "Separation of Concerns"], descriptionHint: "Separate presentation, business, data, and infrastructure concerns.", rx: /\blayered\b/i },
    { title: "Event-Driven Communication", tags: ["Decoupled", "Resilient"], descriptionHint: "Use events/queues to reduce coupling between components.", rx: /\bevent[-\s]?driven\b|\bevents?\b|\bqueue\b|\bkafka\b|\brabbitmq\b/i },
    { title: "API Gateway Pattern", tags: ["Security", "Routing"], descriptionHint: "Centralized entry point for clients with routing and auth.", rx: /\bapi gateway\b|\bgateway\b/i },
    { title: "CQRS", tags: ["Scalable Reads", "Clear Workflows"], descriptionHint: "Separate read and write models for performance and clarity.", rx: /\bcqrs\b/i },
  ];

  for (const k of keywords) {
    if (k.rx.test(source)) {
      picked.push({
        title: k.title,
        description: k.descriptionHint,
        confidence: 80,
        tags: k.tags,
      });
    }
    if (picked.length >= 3) break;
  }

  if (picked.length) return picked;

  // Fallback: build from first few bullets in the plan
  const bullets = takeBullets(plan, 3);
  return bullets.map((b) => ({
    title: b.length > 60 ? `${b.slice(0, 57)}...` : b,
    description: "Derived from the generated architecture plan.",
    confidence: 70,
    tags: ["Generated"],
  }));
}

function buildDecisions(plan: string, report: string): Decision[] {
  const candidates = [
    ...takeBullets(extractSection(plan, /key decisions?/i), 6),
    ...takeBullets(extractSection(plan, /decisions?/i), 6),
    ...takeBullets(extractSection(report, /recommendations?/i), 6),
  ].filter(Boolean);

  const lines = candidates.length ? candidates : takeBullets(plan, 6);
  return lines.slice(0, 4).map((l) => {
    const parts = l.split(/:\s+|\s+-\s+/).map((p) => p.trim()).filter(Boolean);
    const decision = parts[0] || l;
    const justification = parts.slice(1).join(" - ") || "Justification derived from agent output.";
    return { decision, justification };
  });
}

function buildRisks(report: string): Risk[] {
  const r: Risk[] = [];
  const lines = (report || "").split("\n").map((l) => l.trim()).filter(Boolean);

  const add = (severity: Risk["severity"], title: string, description: string) => {
    r.push({
      title: title || "Risk",
      severity,
      description: description || "Derived from analysis report.",
      mitigation: "Mitigation derived from recommendations in the analysis/plan.",
    });
  };

  for (const line of lines) {
    // e.g. "High: Database bottleneck ..."
    const m = /^(high|medium|low)\s*:\s*(.+)$/i.exec(line);
    if (m) {
      const sev = m[1].toLowerCase() as Risk["severity"];
      add(sev, m[2].slice(0, 60), m[2]);
    }
    if (r.length >= 3) break;
  }

  if (r.length) return r;

  const bullets = takeBullets(report, 3);
  return bullets.map((b, idx) => ({
    title: b.length > 60 ? `${b.slice(0, 57)}...` : b,
    severity: idx === 0 ? "high" : idx === 1 ? "medium" : "low",
    description: "Derived from analysis report.",
    mitigation: "Mitigation derived from architecture recommendations.",
  }));
}

function buildRoadmap(plan: string): RoadmapPhase[] {
  const section = extractSection(plan, /roadmap|phases|timeline/i);
  const lines = (section || plan).split("\n").map((l) => l.trim());

  const phases: RoadmapPhase[] = [];
  let current: RoadmapPhase | null = null;

  for (const l of lines) {
    const h = /^(?:#+\s*)?(phase\s*\d+|month\s*\d+(?:\s*-\s*\d+)?|weeks?\s*\d+(?:\s*-\s*\d+)?)\b[:\-–—]?\s*(.*)$/i.exec(l);
    if (h) {
      if (current) phases.push(current);
      const label = `${h[1]}${h[2] ? ` - ${h[2]}` : ""}`.trim();
      current = { month: label, items: [] };
      continue;
    }
    const b = /^[-*]\s+(.+)$/.exec(l);
    if (b) {
      if (!current) current = { month: "Phase 1", items: [] };
      current.items.push(b[1].trim());
    }
    if (phases.length >= 3) break;
  }
  if (current) phases.push(current);

  const cleaned = phases
    .map((p) => ({ ...p, items: p.items.filter(Boolean).slice(0, 6) }))
    .filter((p) => p.items.length > 0)
    .slice(0, 3);

  if (cleaned.length) return cleaned;

  // Minimal fallback using plan bullets
  const bullets = takeBullets(plan, 9);
  return [
    { month: "Phase 1", items: bullets.slice(0, 3) },
    { month: "Phase 2", items: bullets.slice(3, 6) },
    { month: "Phase 3", items: bullets.slice(6, 9) },
  ].filter((p) => p.items.length);
}

function buildScores(plan: string, report: string) {
  const text = `${plan}\n\n${report}`.toLowerCase();
  // Seed values
  let scalability = 70;
  let performance = 70;
  let maintainability = 70;
  let security = 70;

  if (/\bmicroservices?\b/.test(text)) scalability += 12;
  if (/\bkubernetes\b|\bautoscal/i.test(text)) scalability += 8;
  if (/\bcache\b|\bredis\b/.test(text)) performance += 10;
  if (/\bcdn\b|\bqueue\b|\bkafka\b|\brabbitmq\b/.test(text)) performance += 6;
  if (/\bclean architecture\b|\bhexagonal\b|\blayered\b|\bmodular\b|\bbounded context\b/.test(text)) maintainability += 12;
  if (/\bddd\b|\bsolid\b|\binterface\b/.test(text)) maintainability += 6;
  if (/\bauth\b|\boauth\b|\bjwt\b|\brbac\b|\bsecurity\b|\bencrypt\b|\btls\b/.test(text)) security += 12;
  if (/\baudit\b|\brate limit\b|\bthreat\b|\bowasp\b/.test(text)) security += 6;

  const scores = [
    { label: "Scalability", value: clamp01to100(scalability), icon: TrendingUp, color: "text-primary" },
    { label: "Performance", value: clamp01to100(performance), icon: Zap, color: "text-accent" },
    { label: "Maintainability", value: clamp01to100(maintainability), icon: GitBranch, color: "text-success" },
    { label: "Security", value: clamp01to100(security), icon: Shield, color: "text-warning" },
  ];
  return scores;
}

function fromStructuredResults(r: AnalyzeResults) {
  const recommendations: Recommendation[] =
    (r.recommended_patterns || []).map((p) => ({
      title: p.pattern,
      description: p.why,
      confidence: clamp01to100(p.confidence ?? 0),
      tags: (p.tags || []).filter(Boolean),
    })) || [];

  const decisions: Decision[] =
    (r.key_decisions || []).map((d) => ({
      decision: d.decision,
      justification:
        [d.rationale, (d.alternatives || []).length ? `Alternatives: ${(d.alternatives || []).join(", ")}` : ""]
          .filter(Boolean)
          .join("\n"),
    })) || [];

  const risks: Risk[] =
    (r.risk_analysis || []).map((x) => ({
      title: x.risk,
      severity: (x.severity || "medium").toString().toLowerCase() as any,
      description: [x.impact ? `Impact: ${x.impact}` : "", x.likelihood ? `Likelihood: ${x.likelihood}` : ""]
        .filter(Boolean)
        .join(" · "),
      mitigation: x.mitigation,
    })) || [];

  const roadmap: RoadmapPhase[] =
    (r.evolution_roadmap || []).map((ph) => ({
      month: `${ph.phase}${ph.timeframe ? ` (${ph.timeframe})` : ""}`,
      items: [...(ph.goals || []), ...(ph.deliverables || [])].filter(Boolean).slice(0, 8),
    })) || [];

  const indicators = r.indicators;
  const scores =
    indicators
      ? [
          { label: "Scalability", value: clamp01to100(indicators.scalability), icon: TrendingUp, color: "text-primary" },
          { label: "Performance", value: clamp01to100(indicators.performance), icon: Zap, color: "text-accent" },
          { label: "Maintainability", value: clamp01to100(indicators.maintainability), icon: GitBranch, color: "text-success" },
          { label: "Security", value: clamp01to100(indicators.security), icon: Shield, color: "text-warning" },
        ]
      : null;

  return { recommendations, decisions, risks, roadmap, scores };
}

export default function Results() {
  const last = loadLastResult();
  const plan = last?.architecture_plan || "";
  const report = last?.analysis_report || "";

  const structured = last?.results || null;
  const structuredView = structured ? fromStructuredResults(structured) : null;

  const recommendations =
    structuredView?.recommendations?.length ? structuredView.recommendations : buildRecommendations(plan, report);
  const decisions = structuredView?.decisions?.length ? structuredView.decisions : buildDecisions(plan, report);
  const risks = structuredView?.risks?.length ? structuredView.risks : buildRisks(report || plan);
  const roadmap = structuredView?.roadmap?.length ? structuredView.roadmap : buildRoadmap(plan);
  const scores = structuredView?.scores?.length ? structuredView.scores : buildScores(plan, report);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-16">
        <div className="container mx-auto px-4">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <h1 className="text-3xl sm:text-4xl font-bold mb-4">
              <span className="text-foreground">Architecture </span>
              <span className="gradient-text">Analysis Results</span>
            </h1>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Comprehensive recommendations and insights from our AI agents
            </p>
          </motion.div>

          {!last && (
            <div className="glass-card p-6 mb-8">
              <p className="text-sm text-muted-foreground">
                No generated result found. Run an analysis from Project Setup to populate this page.
              </p>
              <div className="mt-4">
                <Button variant="hero" asChild>
                  <Link to="/setup?mode=greenfield">Go to Project Setup</Link>
                </Button>
              </div>
            </div>
          )}

          {/* Score Cards */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
          >
            {scores.map((score, index) => (
              <div key={score.label} className="glass-card p-6 text-center">
                <score.icon className={`h-8 w-8 mx-auto mb-3 ${score.color}`} />
                <p className="text-3xl font-bold text-foreground mb-1">{score.value}</p>
                <p className="text-sm text-muted-foreground">{score.label}</p>
                <Progress value={score.value} className="mt-3 h-1.5" />
              </div>
            ))}
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Recommended Architecture */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-card p-6"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/20">
                  <Layers className="h-5 w-5 text-primary" />
                </div>
                <h2 className="text-xl font-semibold text-foreground">Recommended Patterns</h2>
              </div>

              <div className="space-y-4">
                {recommendations.map((rec, index) => (
                  <div key={rec.title} className="p-4 rounded-lg bg-secondary/30 border border-border/50">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-medium text-foreground">{rec.title}</h3>
                      <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-1 rounded">
                        {rec.confidence}% match
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-3">{rec.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {rec.tags.map(tag => (
                        <span key={tag} className="text-xs px-2 py-1 rounded bg-secondary text-secondary-foreground">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Key Decisions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass-card p-6"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/20">
                  <CheckCircle2 className="h-5 w-5 text-accent" />
                </div>
                <h2 className="text-xl font-semibold text-foreground">Key Decisions</h2>
              </div>

              <div className="space-y-4">
                {decisions.map((item, index) => (
                  <div key={index} className="p-4 rounded-lg bg-secondary/30 border border-border/50">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0 mt-0.5" />
                      <div>
                        <h3 className="font-medium text-foreground mb-1">{item.decision}</h3>
                        <p className="text-sm text-muted-foreground">{item.justification}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Risk Analysis */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="glass-card p-6"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/20">
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                </div>
                <h2 className="text-xl font-semibold text-foreground">Risk Analysis</h2>
              </div>

              <div className="space-y-4">
                {risks.map((risk, index) => (
                  <div key={index} className="p-4 rounded-lg bg-secondary/30 border border-border/50">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-medium text-foreground">{risk.title}</h3>
                      <span className={`text-xs font-medium px-2 py-1 rounded ${
                        risk.severity === "high" ? "bg-destructive/20 text-destructive" :
                        risk.severity === "medium" ? "bg-warning/20 text-warning" :
                        "bg-success/20 text-success"
                      }`}>
                        {risk.severity}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{risk.description}</p>
                    <p className="text-sm text-primary">
                      <span className="font-medium">Mitigation:</span> {risk.mitigation}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Evolution Roadmap */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="glass-card p-6"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/20">
                  <BarChart3 className="h-5 w-5 text-warning" />
                </div>
                <h2 className="text-xl font-semibold text-foreground">Evolution Roadmap</h2>
              </div>

              <div className="space-y-6">
                {roadmap.map((phase, phaseIndex) => (
                  <div key={phase.month} className="relative">
                    {phaseIndex < roadmap.length - 1 && (
                      <div className="absolute left-3 top-8 bottom-0 w-0.5 bg-border" />
                    )}
                    <div className="flex items-start gap-4">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                        {phaseIndex + 1}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-foreground mb-2">{phase.month}</h4>
                        <ul className="space-y-1">
                          {phase.items.map((item, itemIndex) => (
                            <li key={itemIndex} className="flex items-center gap-2 text-sm text-muted-foreground">
                              <ChevronRight className="h-3 w-3 text-primary" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="flex flex-col sm:flex-row justify-center gap-4 mt-12"
          >
            <Button variant="hero" size="lg" asChild>
              <Link to="/reports">
                Download Report
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link to="/visualization">
                View Architecture Diagrams
              </Link>
            </Button>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
