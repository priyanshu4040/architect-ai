import {
  BrownfieldStructuredOutput,
  DetectedApiItem,
  DetectedModuleItem,
  DetectedStack,
  DetectedTechStackDetail,
  IssueItem,
  SuggestedModuleItem,
} from "@/lib/api";

function asIssues(items: IssueItem[] | string[] | undefined): IssueItem[] {
  if (!items?.length) return [];
  if (typeof items[0] === "string") {
    return (items as string[]).map((s) => ({
      issue: s,
      severity: "Medium",
      reason: "",
      suggested_fix: "",
    }));
  }
  return items as IssueItem[];
}

function asStack(stack: BrownfieldStructuredOutput["detected_stack"]): DetectedStack {
  if (Array.isArray(stack)) {
    return { backend: stack.join(", ") };
  }
  return stack || {};
}

function normalizeModules(
  raw: BrownfieldStructuredOutput["detected_modules"]
): DetectedModuleItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (typeof item === "string") {
      return { name: item, type: "unknown", evidence: "", confidence: "low" };
    }
    return item as DetectedModuleItem;
  });
}

function normalizeSuggested(raw: SuggestedModuleItem[] | undefined): SuggestedModuleItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter((m) => m?.name);
}

function normalizeApis(raw: BrownfieldStructuredOutput["detected_apis"]): DetectedApiItem[] {
  if (!Array.isArray(raw)) return [];
  if (raw.length > 0 && typeof raw[0] === "string") return [];
  return raw as DetectedApiItem[];
}

function TechStackSection({ tech }: { tech: DetectedTechStackDetail }) {
  const pcts = tech.language_percentages || {};
  const evidence = tech.evidence || {};

  const renderCategory = (title: string, items: string[] | undefined) => {
    if (!items?.length) return null;
    return (
      <div className="mb-4">
        <h3 className="text-sm font-medium mb-2">{title}</h3>
        <ul className="space-y-1 text-sm text-muted-foreground">
          {items.map((name) => (
            <li key={name}>
              <span className="text-foreground font-medium">{name}</span>
              {pcts[name] != null && title === "Languages" && (
                <span className="ml-1">— {pcts[name]}%</span>
              )}
              {evidence[name]?.length ? (
                <span className="block text-xs mt-0.5">
                  found in {evidence[name].slice(0, 3).join(", ")}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const hasAny =
    tech.languages?.length ||
    tech.frameworks?.length ||
    tech.databases?.length ||
    tech.build_tools?.length ||
    tech.deployment?.length;

  if (!hasAny) {
    return (
      <p className="text-sm text-muted-foreground">
        No clear tech stack detected. Please upload a valid source-code ZIP.
      </p>
    );
  }

  return (
    <>
      <p className="text-xs text-muted-foreground mb-4">
        Tech stack is extracted from uploaded source files using deterministic scanning before AI analysis.
      </p>
      {renderCategory("Languages", tech.languages)}
      {renderCategory("Frameworks", tech.frameworks)}
      {renderCategory("Libraries", tech.libraries)}
      {renderCategory("Databases", tech.databases)}
      {renderCategory("Build tools", tech.build_tools)}
      {renderCategory("Deployment", tech.deployment)}
      {renderCategory("Package managers", tech.package_managers)}
    </>
  );
}

export function BrownfieldSections({ data }: { data: BrownfieldStructuredOutput }) {
  const stack = asStack(data.detected_stack);
  const techStack = data.detected_tech_stack;
  const detectedModules = normalizeModules(data.detected_modules);
  const suggestedModules = normalizeSuggested(data.suggested_modules);
  const detectedApis = normalizeApis(data.detected_apis);
  const evo = data.evolution_plan;
  const evolution =
    evo && !Array.isArray(evo)
      ? evo
      : { immediate_fixes: [], short_term_improvements: [], long_term_improvements: [] };

  return (
    <div className="space-y-8 mb-8">
      {data.message && data.is_fallback && data.fallback_type === "parser_only" && (
        <div className="glass-card p-4 border border-warning/40 text-sm text-warning">
          {data.message}
        </div>
      )}
      {data.structured_partial && data.message && !data.is_fallback && (
        <div className="glass-card p-4 border border-primary/30 text-sm text-muted-foreground">
          {data.message}
        </div>
      )}

      <section className="glass-card p-6">
        <h2 className="text-lg font-semibold mb-2">Project Summary</h2>
        <p className="text-sm text-muted-foreground">{data.project_summary || "—"}</p>
      </section>

      <section className="glass-card p-6">
        <h2 className="text-lg font-semibold mb-4">Detected Tech Stack</h2>
        {techStack ? (
          <TechStackSection tech={techStack} />
        ) : (
          <>
            <p className="text-xs text-muted-foreground mb-4">
              Tech stack is extracted from uploaded source files using deterministic scanning before AI analysis.
            </p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <p><span className="text-muted-foreground">Frontend:</span> {stack.frontend || "—"}</p>
              <p><span className="text-muted-foreground">Backend:</span> {stack.backend || "—"}</p>
              <p><span className="text-muted-foreground">Database:</span> {stack.database || "—"}</p>
              <p><span className="text-muted-foreground">Auth:</span> {stack.authentication || "—"}</p>
              <p><span className="text-muted-foreground">API style:</span> {stack.api_style || "—"}</p>
              <p><span className="text-muted-foreground">Deploy:</span> {(stack.deployment || []).join(", ") || "—"}</p>
            </div>
          </>
        )}
      </section>

      <section className="glass-card p-6">
        <h2 className="text-lg font-semibold mb-4">Detected Modules</h2>
        {detectedModules.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No clear modules detected from uploaded ZIP.
          </p>
        ) : (
          <ul className="space-y-2 text-sm">
            {detectedModules.map((m, i) => (
              <li key={i} className="p-3 rounded-lg bg-secondary/30 border border-border/50">
                <div className="flex justify-between gap-2">
                  <span className="font-medium">{m.name}</span>
                  {m.confidence && (
                    <span className="text-xs text-muted-foreground">{m.confidence}</span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {m.type && <span className="mr-2">Type: {m.type}</span>}
                  {(m.evidence || m.path) && <span>Evidence: {m.evidence || m.path}</span>}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {suggestedModules.length > 0 && (
        <section className="glass-card p-6">
          <h2 className="text-lg font-semibold mb-4">Suggested Modules</h2>
          <ul className="space-y-2 text-sm">
            {suggestedModules.map((m, i) => (
              <li key={i} className="p-3 rounded-lg bg-secondary/20 border border-dashed border-border/50">
                <span className="font-medium">{m.name}</span>
                {m.priority && (
                  <span className="ml-2 text-xs text-muted-foreground">({m.priority})</span>
                )}
                {m.reason && <p className="text-muted-foreground mt-1">{m.reason}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="glass-card p-6">
        <h2 className="text-lg font-semibold mb-4">Detected APIs</h2>
        {detectedApis.length === 0 ? (
          <p className="text-sm text-muted-foreground">No API routes detected in uploaded code.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="pb-2">Method</th>
                  <th className="pb-2">Path</th>
                  <th className="pb-2">File</th>
                </tr>
              </thead>
              <tbody>
                {detectedApis.map((api, i) => (
                  <tr key={i} className="border-b border-border/40">
                    <td className="py-2 pr-2 font-medium">{api.method}</td>
                    <td className="py-2 pr-2">{api.path}</td>
                    <td className="py-2 text-muted-foreground text-xs">{api.file || api.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {Array.isArray(data.folder_analysis) && data.folder_analysis.length > 0 && (
        <section className="glass-card p-6">
          <h2 className="text-lg font-semibold mb-4">Folder Analysis</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="pb-2">Folder</th>
                  <th className="pb-2">Purpose</th>
                  <th className="pb-2">Quality</th>
                  <th className="pb-2">Suggestion</th>
                </tr>
              </thead>
              <tbody>
                {(typeof data.folder_analysis[0] === "string"
                  ? (data.folder_analysis as string[]).map((f) => ({
                      folder: f,
                      purpose: "",
                      quality: "",
                      suggestion: "",
                    }))
                  : data.folder_analysis
                ).map((row, i) => (
                  <tr key={i} className="border-b border-border/40">
                    <td className="py-2 pr-2 font-medium">{row.folder}</td>
                    <td className="py-2 pr-2">{row.purpose}</td>
                    <td className="py-2 pr-2">{row.quality}</td>
                    <td className="py-2 text-muted-foreground">{row.suggestion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <IssueTable title="Architecture Issues" issues={asIssues(data.architecture_issues)} showArea />
      <IssueTable title="Security Issues" issues={asIssues(data.security_issues)} />
      <IssueTable title="Scalability Issues" issues={asIssues(data.scalability_issues)} />
      <IssueTable title="Maintainability Issues" issues={asIssues(data.maintainability_issues)} />

      <section className="glass-card p-6">
        <h2 className="text-lg font-semibold mb-4">Evolution Plan</h2>
        <div className="grid md:grid-cols-3 gap-4 text-sm">
          <div>
            <h3 className="font-medium text-destructive mb-2">Immediate</h3>
            <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
              {(evolution.immediate_fixes || []).map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-warning mb-2">Short-term</h3>
            <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
              {(evolution.short_term_improvements || []).map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-primary mb-2">Long-term</h3>
            <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
              {(evolution.long_term_improvements || []).map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

function IssueTable({
  title,
  issues,
  showArea,
}: {
  title: string;
  issues: IssueItem[];
  showArea?: boolean;
}) {
  if (!issues.length) return null;
  return (
    <section className="glass-card p-6">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      <div className="space-y-3">
        {issues.map((item, i) => (
          <div key={i} className="p-3 rounded-lg bg-secondary/30 border border-border/50 text-sm">
            <div className="flex justify-between gap-2 mb-1">
              <span className="font-medium">{item.issue}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded ${
                  item.severity?.toLowerCase() === "high"
                    ? "bg-destructive/20 text-destructive"
                    : item.severity?.toLowerCase() === "low"
                      ? "bg-success/20 text-success"
                      : "bg-warning/20 text-warning"
                }`}
              >
                {item.severity}
              </span>
            </div>
            {item.reason && <p className="text-muted-foreground">{item.reason}</p>}
            {item.suggested_fix && <p className="text-primary mt-1">Fix: {item.suggested_fix}</p>}
            {showArea && (item.affected_area || item.affected_file_or_folder) && (
              <p className="text-xs text-muted-foreground mt-1">
                Area: {item.affected_area || item.affected_file_or_folder}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}