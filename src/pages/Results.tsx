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

const recommendations = [
  {
    title: "Microservices Architecture",
    description: "Recommended for your scalability requirements and team structure",
    confidence: 92,
    tags: ["Scalable", "Maintainable", "Team-friendly"],
  },
  {
    title: "Event-Driven Communication",
    description: "Use message queues for inter-service communication",
    confidence: 88,
    tags: ["Decoupled", "Resilient"],
  },
  {
    title: "API Gateway Pattern",
    description: "Centralized entry point for all client requests",
    confidence: 95,
    tags: ["Security", "Routing"],
  },
];

const decisions = [
  {
    decision: "Use PostgreSQL for primary data store",
    justification: "Strong consistency requirements, complex queries, and mature ecosystem support your needs",
  },
  {
    decision: "Implement Redis caching layer",
    justification: "High read frequency and performance requirements justify an in-memory cache",
  },
  {
    decision: "Deploy on Kubernetes",
    justification: "Scalability needs and microservices architecture benefit from container orchestration",
  },
];

const risks = [
  {
    title: "Database Bottleneck Risk",
    severity: "high",
    description: "Order database shows signs of becoming a bottleneck at scale",
    mitigation: "Consider read replicas and query optimization",
  },
  {
    title: "Service Coupling",
    severity: "medium",
    description: "Order and User services have tight coupling",
    mitigation: "Introduce event-driven patterns for decoupling",
  },
  {
    title: "Cache Invalidation",
    severity: "low",
    description: "Complex cache invalidation logic in analytics service",
    mitigation: "Implement time-based TTL with eventual consistency",
  },
];

const roadmap = [
  { month: "Month 1-2", items: ["Set up API Gateway", "Implement authentication service", "Database schema design"] },
  { month: "Month 3-4", items: ["Core microservices development", "Message queue integration", "Initial deployment pipeline"] },
  { month: "Month 5-6", items: ["Caching layer implementation", "Performance optimization", "Monitoring & observability"] },
];

const scores = [
  { label: "Scalability", value: 85, icon: TrendingUp, color: "text-primary" },
  { label: "Performance", value: 78, icon: Zap, color: "text-accent" },
  { label: "Maintainability", value: 82, icon: GitBranch, color: "text-success" },
  { label: "Security", value: 90, icon: Shield, color: "text-warning" },
];

export default function Results() {
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
                Download Full Report
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
