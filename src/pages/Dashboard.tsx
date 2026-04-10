import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  Bot, 
  BrainCircuit, 
  CheckCircle2, 
  Clock, 
  Loader2, 
  MessageSquare,
  ChevronRight,
  Eye
} from "lucide-react";
import { Link } from "react-router-dom";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { loadLastResult } from "@/lib/api";

type AgentStatus = "idle" | "running" | "complete";

interface AgentState {
  analysisAgent: {
    status: AgentStatus;
    currentTask: string;
    progress: number;
    outputs: string[];
  };
  planningAgent: {
    status: AgentStatus;
    currentTask: string;
    progress: number;
    outputs: string[];
  };
}

const initialAgentState: AgentState = {
  analysisAgent: {
    status: "idle",
    currentTask: "Waiting to start...",
    progress: 0,
    outputs: [],
  },
  planningAgent: {
    status: "idle",
    currentTask: "Waiting for analysis...",
    progress: 0,
    outputs: [],
  },
};

const analysisSteps = [
  { task: "Parsing project structure", duration: 2000 },
  { task: "Analyzing module dependencies", duration: 2500 },
  { task: "Identifying architecture patterns", duration: 2000 },
  { task: "Evaluating code quality metrics", duration: 1500 },
  { task: "Generating analysis report", duration: 1000 },
];

const planningSteps = [
  { task: "Processing analysis insights", duration: 1500 },
  { task: "Evaluating architecture patterns", duration: 2000 },
  { task: "Calculating scalability projections", duration: 2000 },
  { task: "Formulating recommendations", duration: 2500 },
  { task: "Creating evolution roadmap", duration: 1500 },
];

export default function Dashboard() {
  const [agents, setAgents] = useState<AgentState>(initialAgentState);
  const [timeline, setTimeline] = useState<{ time: string; event: string; agent: string }[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    const runAgents = async () => {
      const last = loadLastResult();
      // Start Analysis Agent
      setAgents(prev => ({
        ...prev,
        analysisAgent: { ...prev.analysisAgent, status: "running" }
      }));
      addTimelineEvent("Analysis Agent started", "analysis");

      // Run analysis steps
      for (let i = 0; i < analysisSteps.length; i++) {
        const step = analysisSteps[i];
        setAgents(prev => ({
          ...prev,
          analysisAgent: {
            ...prev.analysisAgent,
            currentTask: step.task,
            progress: ((i + 1) / analysisSteps.length) * 100,
          }
        }));
        await sleep(step.duration);
        addTimelineEvent(`Completed: ${step.task}`, "analysis");
      }

      setAgents(prev => ({
        ...prev,
        analysisAgent: { 
          ...prev.analysisAgent, 
          status: "complete",
          currentTask: "Analysis complete",
          outputs: last?.analysis_report
            ? last.analysis_report
                .split("\n")
                .map((l) => l.trim())
                .filter(Boolean)
                .slice(0, 5)
            : [
                "No analysis report found. Run an analysis from Project Setup.",
              ],
        }
      }));
      addTimelineEvent("Analysis Agent completed", "analysis");

      // Start Planning Agent
      setAgents(prev => ({
        ...prev,
        planningAgent: { ...prev.planningAgent, status: "running" }
      }));
      addTimelineEvent("Planning Agent started", "planning");

      // Run planning steps
      for (let i = 0; i < planningSteps.length; i++) {
        const step = planningSteps[i];
        setAgents(prev => ({
          ...prev,
          planningAgent: {
            ...prev.planningAgent,
            currentTask: step.task,
            progress: ((i + 1) / planningSteps.length) * 100,
          }
        }));
        await sleep(step.duration);
        addTimelineEvent(`Completed: ${step.task}`, "planning");
      }

      setAgents(prev => ({
        ...prev,
        planningAgent: { 
          ...prev.planningAgent, 
          status: "complete",
          currentTask: "Planning complete",
          outputs: last?.architecture_plan
            ? last.architecture_plan
                .split("\n")
                .map((l) => l.trim())
                .filter(Boolean)
                .slice(0, 5)
            : [
                "No architecture plan found. Run an analysis from Project Setup.",
              ],
        }
      }));
      addTimelineEvent("Planning Agent completed", "planning");
      setIsComplete(true);
    };

    runAgents();
  }, []);

  const addTimelineEvent = (event: string, agent: string) => {
    const time = new Date().toLocaleTimeString();
    setTimeline(prev => [...prev, { time, event, agent }]);
  };

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

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
              <span className="text-foreground">Agent </span>
              <span className="gradient-text">Dashboard</span>
            </h1>
            <p className="text-muted-foreground">
              Watch the AI agents collaborate in real-time
            </p>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Agent Cards */}
            <div className="lg:col-span-2 space-y-6">
              {/* Analysis Agent */}
              <AgentCard
                icon={BrainCircuit}
                name="Architecture Analysis Agent"
                description="Analyzes code structure, dependencies, and patterns"
                status={agents.analysisAgent.status}
                currentTask={agents.analysisAgent.currentTask}
                progress={agents.analysisAgent.progress}
                outputs={agents.analysisAgent.outputs}
                color="primary"
              />

              {/* Planning Agent */}
              <AgentCard
                icon={Bot}
                name="Architecture Planning & Decision Agent"
                description="Recommends patterns, decisions, and evolution strategies"
                status={agents.planningAgent.status}
                currentTask={agents.planningAgent.currentTask}
                progress={agents.planningAgent.progress}
                outputs={agents.planningAgent.outputs}
                color="accent"
              />

              {/* Action Buttons */}
              {isComplete && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col sm:flex-row gap-4"
                >
                  <Button variant="hero" size="lg" className="flex-1" asChild>
                    <Link to="/visualization">
                      <Eye className="mr-2 h-5 w-5" />
                      View Architecture
                    </Link>
                  </Button>
                  <Button variant="outline" size="lg" className="flex-1" asChild>
                    <Link to="/results">
                      View Full Results
                      <ChevronRight className="ml-2 h-5 w-5" />
                    </Link>
                  </Button>
                </motion.div>
              )}
            </div>

            {/* Timeline */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Clock className="h-5 w-5 text-primary" />
                Activity Timeline
              </h3>
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                {timeline.map((item, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`flex items-start gap-3 text-sm ${
                      item.agent === "analysis" ? "text-primary" : "text-accent"
                    }`}
                  >
                    <MessageSquare className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <span className="text-xs text-muted-foreground">{item.time}</span>
                      <p className="text-foreground">{item.event}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function AgentCard({
  icon: Icon,
  name,
  description,
  status,
  currentTask,
  progress,
  outputs,
  color,
}: {
  icon: React.ElementType;
  name: string;
  description: string;
  status: AgentStatus;
  currentTask: string;
  progress: number;
  outputs: string[];
  color: "primary" | "accent";
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass-card p-6 ${status === "running" ? "animate-pulse-glow" : ""}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${
            color === "primary" ? "from-primary to-primary/50" : "from-accent to-accent/50"
          }`}>
            <Icon className={`h-6 w-6 ${color === "primary" ? "text-primary-foreground" : "text-accent-foreground"}`} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">{name}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </div>
        <StatusBadge status={status} />
      </div>

      {/* Current Task */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          {status === "running" && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
          {status === "complete" && <CheckCircle2 className="h-4 w-4 text-success" />}
          <span className="text-sm text-muted-foreground">Current Task</span>
        </div>
        <p className="text-foreground">{currentTask}</p>
      </div>

      {/* Progress */}
      {status === "running" && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      )}

      {/* Outputs */}
      {outputs.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border/50">
          <p className="text-sm text-muted-foreground mb-2">Key Findings</p>
          <ul className="space-y-1">
            {outputs.map((output, index) => (
              <li key={index} className="flex items-center gap-2 text-sm text-foreground">
                <CheckCircle2 className="h-3 w-3 text-success flex-shrink-0" />
                {output}
              </li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
}

function StatusBadge({ status }: { status: AgentStatus }) {
  const config = {
    idle: { label: "Idle", className: "bg-muted text-muted-foreground" },
    running: { label: "Running", className: "bg-primary/20 text-primary" },
    complete: { label: "Complete", className: "bg-success/20 text-success" },
  };

  const { label, className } = config[status];

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${className}`}>
      {status === "running" && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
      {label}
    </span>
  );
}
