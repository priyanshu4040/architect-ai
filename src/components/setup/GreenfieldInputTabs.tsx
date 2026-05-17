import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import {
  compileRequirements,
  getTemplate,
  listTemplates,
  NfrSuggestResponse,
  ProjectTemplate,
  RequirementsCompileResponse,
  suggestNfr,
} from "@/lib/api";
import { toast } from "sonner";
import { notifyApiError } from "@/lib/apiErrors";

export type RequirementInputMode = "manual" | "guided" | "template";

type Props = {
  functionalRequirements: string;
  onRequirementsChange: (text: string) => void;
  scalability: number;
  performance: number;
  maintainability: number;
  security: number;
  expectedUsers: string;
  growthRate: string;
  onNfrChange: (key: string, value: number | string) => void;
};

export function GreenfieldInputTabs(props: Props) {
  const [tab, setTab] = useState<RequirementInputMode>("manual");
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [templateBody, setTemplateBody] = useState<Record<string, unknown> | null>(null);
  const [loadingTpl, setLoadingTpl] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestion, setSuggestion] = useState<NfrSuggestResponse | null>(null);

  const [guided, setGuided] = useState({
    project_type: "",
    users: "",
    features: "",
    authentication: "Yes",
    database: "Yes",
    project_level: "Mini Project",
    preferred_technology: "Not sure",
    deployment: "Not sure",
  });

  useEffect(() => {
    listTemplates().then(setTemplates).catch(() => {});
  }, []);

  const applyCompiled = (compiled: RequirementsCompileResponse) => {
    props.onRequirementsChange(compiled.generated_requirement_summary);
    toast.success(`Requirements compiled (${compiled.requirement_source})`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {(
          [
            ["manual", "Manual Input"],
            ["guided", "Guided Prompts"],
            ["template", "Templates"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${
              tab === id ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "manual" && (
        <ManualSection
          {...props}
          isSuggesting={isSuggesting}
          setIsSuggesting={setIsSuggesting}
          suggestion={suggestion}
          setSuggestion={setSuggestion}
        />
      )}
      {tab === "guided" && (
        <GuidedSection
          guided={guided}
          setGuided={setGuided}
          onCompile={async () => {
            try {
              applyCompiled(await compileRequirements({ source: "guided", answers: { ...guided } }));
            } catch (e) {
              notifyApiError(e);
            }
          }}
        />
      )}
      {tab === "template" && (
        <TemplateSection
          templates={templates}
          selectedTemplate={selectedTemplate}
          loadingTpl={loadingTpl}
          templateBody={templateBody}
          onSelect={async (id) => {
            setSelectedTemplate(id);
            setLoadingTpl(true);
            try {
              setTemplateBody(await getTemplate(id));
            } catch {
              toast.error("Could not load template");
            } finally {
              setLoadingTpl(false);
            }
          }}
          onBodyChange={setTemplateBody}
          onCompile={async () => {
            if (!selectedTemplate) return;
            try {
              applyCompiled(
                await compileRequirements({
                  source: "template",
                  template_id: selectedTemplate,
                  overrides: templateBody || undefined,
                })
              );
            } catch (e) {
              notifyApiError(e);
            }
          }}
        />
      )}

      <NfrSection {...props} />
    </div>
  );
}

function ManualSection({
  functionalRequirements,
  onRequirementsChange,
  scalability,
  performance,
  maintainability,
  security,
  isSuggesting,
  setIsSuggesting,
  suggestion,
  setSuggestion,
}: Props & {
  isSuggesting: boolean;
  setIsSuggesting: (v: boolean) => void;
  suggestion: NfrSuggestResponse | null;
  setSuggestion: (v: NfrSuggestResponse | null) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Label>Functional Requirements</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isSuggesting}
          className="gap-2"
          onClick={async () => {
            if (!functionalRequirements.trim()) {
              toast.error("Enter requirements first");
              return;
            }
            setIsSuggesting(true);
            try {
              setSuggestion(
                await suggestNfr({
                  prompt: functionalRequirements,
                  scalability,
                  performance,
                  maintainability,
                  security,
                })
              );
            } catch (e) {
              notifyApiError(e);
            } finally {
              setIsSuggesting(false);
            }
          }}
        >
          {isSuggesting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          Improve Prompt
        </Button>
      </div>
      <Textarea
        placeholder="Describe features, users, integrations, scale..."
        value={functionalRequirements}
        onChange={(e) => onRequirementsChange(e.target.value)}
        className="min-h-[140px]"
      />
      {suggestion && (
        <div className="rounded-lg border border-primary/30 p-4 space-y-2 text-sm">
          <p className="font-medium text-primary">AI suggestion</p>
          <p className="text-muted-foreground">{suggestion.improved_prompt}</p>
          <Button type="button" size="sm" variant="hero" onClick={() => onRequirementsChange(suggestion.improved_prompt)}>
            Apply
          </Button>
        </div>
      )}
    </div>
  );
}

function GuidedSection({
  guided,
  setGuided,
  onCompile,
}: {
  guided: Record<string, string>;
  setGuided: (g: Record<string, string>) => void;
  onCompile: () => void;
}) {
  const fields: [string, string, string][] = [
    ["project_type", "Application type", "E-commerce, LMS, Healthcare..."],
    ["users", "Users / roles", "Admin, Customer..."],
    ["features", "Main features", "Login, Dashboard, Payments..."],
    ["authentication", "Authentication", "Yes / Role-based / No"],
    ["database", "Database", "Yes / No / Not sure"],
    ["project_level", "Project level", "Mini Project, MVP, Enterprise"],
    ["preferred_technology", "Preferred stack", "MERN, Spring Boot + React"],
    ["deployment", "Deployment", "Local, Cloud, Docker"],
  ];
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">Answer simple questions — we compile a requirements summary.</p>
      {fields.map(([key, label, ph]) => (
        <div key={key}>
          <Label>{label}</Label>
          <Input
            className="mt-2"
            placeholder={ph}
            value={guided[key] || ""}
            onChange={(e) => setGuided({ ...guided, [key]: e.target.value })}
          />
        </div>
      ))}
      <Button type="button" variant="hero" onClick={onCompile}>
        Generate Requirements Summary
      </Button>
    </div>
  );
}

function TemplateSection({
  templates,
  selectedTemplate,
  loadingTpl,
  templateBody,
  onSelect,
  onBodyChange,
  onCompile,
}: {
  templates: ProjectTemplate[];
  selectedTemplate: string;
  loadingTpl: boolean;
  templateBody: Record<string, unknown> | null;
  onSelect: (id: string) => void;
  onBodyChange: (b: Record<string, unknown>) => void;
  onCompile: () => void;
}) {
  return (
    <div className="space-y-4">
      <Label>Choose a template</Label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
        {templates.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelect(t.id)}
            className={`p-3 rounded-lg border text-left text-sm ${
              selectedTemplate === t.id ? "border-primary bg-primary/5" : "border-border"
            }`}
          >
            {t.name}
          </button>
        ))}
      </div>
      {loadingTpl && <p className="text-sm text-muted-foreground">Loading...</p>}
      {templateBody && (
        <>
          <Label>Edit template (JSON)</Label>
          <Textarea
            className="min-h-[100px] font-mono text-xs"
            value={JSON.stringify(templateBody, null, 2)}
            onChange={(e) => {
              try {
                onBodyChange(JSON.parse(e.target.value));
              } catch {
                /* ignore invalid JSON while typing */
              }
            }}
          />
          <Button type="button" variant="hero" onClick={onCompile}>
            Use Template & Compile
          </Button>
        </>
      )}
    </div>
  );
}

function NfrSection(props: Props) {
  const sliders = [
    ["scalability", props.scalability],
    ["performance", props.performance],
    ["maintainability", props.maintainability],
    ["security", props.security],
  ] as const;
  return (
    <div className="space-y-4 pt-4 border-t border-border/50">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Expected Users</Label>
          <Input
            className="mt-2"
            value={props.expectedUsers}
            onChange={(e) => props.onNfrChange("expectedUsers", e.target.value)}
          />
        </div>
        <div>
          <Label>Growth Rate</Label>
          <Input
            className="mt-2"
            value={props.growthRate}
            onChange={(e) => props.onNfrChange("growthRate", e.target.value)}
          />
        </div>
      </div>
      <Label>NFR Priorities</Label>
      {sliders.map(([key, val]) => (
        <div key={key} className="flex items-center gap-4">
          <span className="w-28 text-sm capitalize text-muted-foreground">{key}</span>
          <Slider
            value={[val]}
            onValueChange={(v) => props.onNfrChange(key, v[0])}
            max={100}
            step={1}
            className="flex-1"
          />
          <span className="w-10 text-right text-sm">{val}%</span>
        </div>
      ))}
    </div>
  );
}
