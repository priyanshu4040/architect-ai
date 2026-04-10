import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams, useNavigate } from "react-router-dom";
import { 
  ArrowLeft, 
  ArrowRight, 
  Check, 
  Code2, 
  Database, 
  GitBranch, 
  Globe, 
  Layers, 
  Server 
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { analyze, analyzeBrownfieldZip, saveLastResult } from "@/lib/api";
import { toast } from "sonner";

type ProjectMode = "greenfield" | "brownfield";
type ProjectDomain = "web-app" | "api" | "distributed" | null;

interface WizardState {
  step: number;
  projectName: string;
  mode: ProjectMode | null;
  domain: ProjectDomain;
  functionalRequirements: string;
  scalability: number;
  performance: number;
  maintainability: number;
  security: number;
  expectedUsers: string;
  growthRate: string;
  brownfieldZip: File | null;
}

const domains = [
  { id: "web-app", label: "Web Application", icon: Globe, description: "Full-stack web apps with UI" },
  { id: "api", label: "API Service", icon: Server, description: "RESTful or GraphQL APIs" },
  { id: "distributed", label: "Distributed System", icon: Database, description: "Microservices & event-driven" },
];

const steps = [
  { id: 1, title: "Project Info", description: "Basic details" },
  { id: 2, title: "Mode & Domain", description: "Project type" },
  { id: 3, title: "Requirements", description: "Specifications" },
  { id: 4, title: "Review", description: "Confirm & submit" },
];

export default function ProjectSetup() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialMode = searchParams.get("mode") as ProjectMode | null;
  
  const [state, setState] = useState<WizardState>({
    step: 1,
    projectName: "",
    mode: initialMode,
    domain: null,
    functionalRequirements: "",
    scalability: 50,
    performance: 50,
    maintainability: 50,
    security: 50,
    expectedUsers: "",
    growthRate: "",
    brownfieldZip: null,
  });

  const updateState = (updates: Partial<WizardState>) => {
    setState(prev => ({ ...prev, ...updates }));
  };

  const canProceed = () => {
    switch (state.step) {
      case 1: return state.projectName.trim().length > 0;
      case 2: return state.mode && state.domain;
      case 3: return state.mode === "brownfield" 
        ? !!state.brownfieldZip
        : state.functionalRequirements.trim().length > 0;
      case 4: return true;
      default: return false;
    }
  };

  const handleSubmit = () => {
    const mode = state.mode;
    if (!mode) return;

    if (mode === "brownfield") {
      if (!state.brownfieldZip) {
        toast.error("Please upload a .zip file.");
        return;
      }
      analyzeBrownfieldZip(state.brownfieldZip)
        .then((result) => {
          saveLastResult(result);
          navigate("/dashboard");
        })
        .catch((err: unknown) => {
          const message = err instanceof Error ? err.message : "Analysis failed";
          toast.error(message);
        });
      return;
    }

    analyze({ mode, input: state.functionalRequirements })
      .then((result) => {
        saveLastResult(result);
        navigate("/dashboard");
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Analysis failed";
        toast.error(message);
      });
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-16">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto">
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center mb-12"
            >
              <h1 className="text-3xl sm:text-4xl font-bold mb-4">
                <span className="text-foreground">Set Up Your </span>
                <span className="gradient-text">Architecture Project</span>
              </h1>
              <p className="text-muted-foreground">
                Configure your project settings to get personalized architecture recommendations
              </p>
            </motion.div>

            {/* Progress Steps */}
            <div className="mb-12">
              <div className="flex items-center justify-between relative">
                <div className="absolute top-5 left-0 right-0 h-0.5 bg-border" />
                <div 
                  className="absolute top-5 left-0 h-0.5 bg-primary transition-all duration-500"
                  style={{ width: `${((state.step - 1) / (steps.length - 1)) * 100}%` }}
                />
                {steps.map((step) => (
                  <div key={step.id} className="relative z-10 flex flex-col items-center">
                    <div 
                      className={`flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                        state.step > step.id 
                          ? "bg-primary border-primary text-primary-foreground"
                          : state.step === step.id
                          ? "bg-secondary border-primary text-primary"
                          : "bg-card border-border text-muted-foreground"
                      }`}
                    >
                      {state.step > step.id ? (
                        <Check className="h-5 w-5" />
                      ) : (
                        <span className="text-sm font-medium">{step.id}</span>
                      )}
                    </div>
                    <div className="mt-2 text-center hidden sm:block">
                      <p className={`text-sm font-medium ${state.step >= step.id ? "text-foreground" : "text-muted-foreground"}`}>
                        {step.title}
                      </p>
                      <p className="text-xs text-muted-foreground">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Step Content */}
            <div className="glass-card p-8">
              <AnimatePresence mode="wait">
                {state.step === 1 && (
                  <StepProjectInfo state={state} updateState={updateState} />
                )}
                {state.step === 2 && (
                  <StepModeAndDomain state={state} updateState={updateState} />
                )}
                {state.step === 3 && (
                  <StepRequirements state={state} updateState={updateState} />
                )}
                {state.step === 4 && (
                  <StepReview state={state} />
                )}
              </AnimatePresence>

              {/* Navigation Buttons */}
              <div className="flex items-center justify-between mt-8 pt-6 border-t border-border/50">
                <Button
                  variant="ghost"
                  onClick={() => updateState({ step: state.step - 1 })}
                  disabled={state.step === 1}
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                
                {state.step < 4 ? (
                  <Button
                    variant="hero"
                    onClick={() => updateState({ step: state.step + 1 })}
                    disabled={!canProceed()}
                  >
                    Continue
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                ) : (
                  <Button variant="hero" onClick={handleSubmit}>
                    Generate Architecture
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function StepProjectInfo({ state, updateState }: { state: WizardState; updateState: (u: Partial<WizardState>) => void }) {
  return (
    <motion.div
      key="step-1"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
    >
      <h2 className="text-xl font-semibold text-foreground mb-6">Project Information</h2>
      <div className="space-y-6">
        <div>
          <Label htmlFor="projectName">Project Name</Label>
          <Input
            id="projectName"
            placeholder="e.g., E-Commerce Platform"
            value={state.projectName}
            onChange={(e) => updateState({ projectName: e.target.value })}
            className="mt-2"
          />
          <p className="text-xs text-muted-foreground mt-2">
            Give your project a descriptive name
          </p>
        </div>
      </div>
    </motion.div>
  );
}

function StepModeAndDomain({ state, updateState }: { state: WizardState; updateState: (u: Partial<WizardState>) => void }) {
  return (
    <motion.div
      key="step-2"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
    >
      <h2 className="text-xl font-semibold text-foreground mb-6">Project Mode & Domain</h2>
      
      {/* Mode Selection */}
      <div className="mb-8">
        <Label className="mb-4 block">Project Mode</Label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            onClick={() => updateState({ mode: "greenfield" })}
            className={`p-4 rounded-xl border-2 text-left transition-all ${
              state.mode === "greenfield"
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50"
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              <Layers className={`h-5 w-5 ${state.mode === "greenfield" ? "text-primary" : "text-muted-foreground"}`} />
              <span className="font-medium text-foreground">Greenfield</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Starting a new project from scratch
            </p>
          </button>
          
          <button
            onClick={() => updateState({ mode: "brownfield" })}
            className={`p-4 rounded-xl border-2 text-left transition-all ${
              state.mode === "brownfield"
                ? "border-accent bg-accent/5"
                : "border-border hover:border-accent/50"
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              <GitBranch className={`h-5 w-5 ${state.mode === "brownfield" ? "text-accent" : "text-muted-foreground"}`} />
              <span className="font-medium text-foreground">Brownfield</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Analyze and evolve existing codebase
            </p>
          </button>
        </div>
      </div>

      {/* Domain Selection */}
      <div>
        <Label className="mb-4 block">Project Domain</Label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {domains.map((domain) => (
            <button
              key={domain.id}
              onClick={() => updateState({ domain: domain.id as ProjectDomain })}
              className={`p-4 rounded-xl border-2 text-center transition-all ${
                state.domain === domain.id
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <domain.icon className={`h-6 w-6 mx-auto mb-2 ${
                state.domain === domain.id ? "text-primary" : "text-muted-foreground"
              }`} />
              <span className="block font-medium text-foreground text-sm">{domain.label}</span>
              <span className="block text-xs text-muted-foreground mt-1">{domain.description}</span>
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function StepRequirements({ state, updateState }: { state: WizardState; updateState: (u: Partial<WizardState>) => void }) {
  return (
    <motion.div
      key="step-3"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
    >
      <h2 className="text-xl font-semibold text-foreground mb-6">
        {state.mode === "brownfield" ? "Code Analysis" : "Project Requirements"}
      </h2>
      
      {state.mode === "brownfield" ? (
        <div className="space-y-6">
          <div>
            <Label htmlFor="zipUpload">Upload Codebase (.zip)</Label>
            <Input
              id="zipUpload"
              type="file"
              accept=".zip,application/zip"
              onChange={(e) => {
                const f = e.target.files?.[0] || null;
                updateState({ brownfieldZip: f });
              }}
              className="mt-2"
            />
            <p className="text-xs text-muted-foreground mt-2">
              Upload a zipped copy of your codebase (GitHub “Download ZIP” also works)
            </p>
          </div>
          <div className="p-4 rounded-lg bg-secondary/30 border border-border/50">
            <div className="flex items-center gap-2 mb-2">
              <Code2 className="h-4 w-4 text-accent" />
              <span className="text-sm font-medium text-foreground">What we'll analyze</span>
            </div>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Code structure and module organization</li>
              <li>• Dependency graphs and coupling analysis</li>
              <li>• Architecture patterns identification</li>
              <li>• Technical debt and risk assessment</li>
            </ul>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div>
            <Label htmlFor="funcReq">Functional Requirements</Label>
            <Textarea
              id="funcReq"
              placeholder="Describe the main features and functionality of your system..."
              value={state.functionalRequirements}
              onChange={(e) => updateState({ functionalRequirements: e.target.value })}
              className="mt-2 min-h-[120px]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <Label>Expected Users</Label>
              <Input
                placeholder="e.g., 10,000"
                value={state.expectedUsers}
                onChange={(e) => updateState({ expectedUsers: e.target.value })}
                className="mt-2"
              />
            </div>
            <div>
              <Label>Growth Rate (monthly)</Label>
              <Input
                placeholder="e.g., 20%"
                value={state.growthRate}
                onChange={(e) => updateState({ growthRate: e.target.value })}
                className="mt-2"
              />
            </div>
          </div>

          <div className="space-y-4">
            <Label className="block">Non-Functional Requirements</Label>
            {[
              { key: "scalability", label: "Scalability" },
              { key: "performance", label: "Performance" },
              { key: "maintainability", label: "Maintainability" },
              { key: "security", label: "Security" },
            ].map((item) => (
              <div key={item.key} className="flex items-center gap-4">
                <span className="w-32 text-sm text-muted-foreground">{item.label}</span>
                <Slider
                  value={[state[item.key as keyof WizardState] as number]}
                  onValueChange={(v) => updateState({ [item.key]: v[0] })}
                  max={100}
                  step={1}
                  className="flex-1"
                />
                <span className="w-12 text-right text-sm text-foreground">
                  {state[item.key as keyof WizardState]}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

function StepReview({ state }: { state: WizardState }) {
  return (
    <motion.div
      key="step-4"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
    >
      <h2 className="text-xl font-semibold text-foreground mb-6">Review & Generate</h2>
      
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-secondary/30 border border-border/50">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Project Name</h3>
          <p className="text-foreground">{state.projectName}</p>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-secondary/30 border border-border/50">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Mode</h3>
            <p className="text-foreground capitalize">{state.mode}</p>
          </div>
          <div className="p-4 rounded-lg bg-secondary/30 border border-border/50">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Domain</h3>
            <p className="text-foreground capitalize">{state.domain?.replace("-", " ")}</p>
          </div>
        </div>

        {state.mode === "brownfield" ? (
          <div className="p-4 rounded-lg bg-secondary/30 border border-border/50">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Codebase ZIP</h3>
            <p className="text-foreground break-all">{state.brownfieldZip?.name || "No file selected"}</p>
          </div>
        ) : (
          <>
            <div className="p-4 rounded-lg bg-secondary/30 border border-border/50">
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Requirements Summary</h3>
              <p className="text-foreground text-sm">{state.functionalRequirements.substring(0, 200)}...</p>
            </div>
            <div className="grid grid-cols-4 gap-4">
              {["scalability", "performance", "maintainability", "security"].map((key) => (
                <div key={key} className="p-3 rounded-lg bg-secondary/30 border border-border/50 text-center">
                  <p className="text-xs text-muted-foreground capitalize">{key}</p>
                  <p className="text-lg font-semibold text-primary">{state[key as keyof WizardState]}%</p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}
