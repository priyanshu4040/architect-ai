import { motion } from "framer-motion";
import { Bot, BrainCircuit, GitCompare, LineChart, Shield, Workflow } from "lucide-react";

const features = [
  {
    icon: BrainCircuit,
    title: "Analysis Agent",
    description: "Intelligent agent that deeply analyzes your codebase, identifying patterns, dependencies, and potential issues.",
    color: "text-primary",
  },
  {
    icon: Bot,
    title: "Planning Agent",
    description: "Strategic agent that recommends architecture patterns, suggests improvements, and creates evolution roadmaps.",
    color: "text-accent",
  },
  {
    icon: Workflow,
    title: "Agentic Collaboration",
    description: "Watch both agents work together in real-time, sharing insights and building comprehensive architecture plans.",
    color: "text-warning",
  },
  {
    icon: GitCompare,
    title: "Greenfield & Brownfield",
    description: "Whether starting fresh or evolving existing systems, our agents adapt to your project context.",
    color: "text-success",
  },
  {
    icon: LineChart,
    title: "Visual Architecture",
    description: "Interactive diagrams showing layered architecture, module dependencies, and system boundaries.",
    color: "text-primary",
  },
  {
    icon: Shield,
    title: "Risk Analysis",
    description: "Identify bottlenecks, security concerns, and scalability issues before they become problems.",
    color: "text-destructive",
  },
];

export function FeaturesSection() {
  return (
    <section className="py-24 relative">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            <span className="text-foreground">Powered by </span>
            <span className="gradient-text">Intelligent Agents</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Two specialized AI agents collaborate to deliver comprehensive architecture insights
            and actionable recommendations.
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="group"
            >
              <div className="glass-card glow-border p-6 h-full transition-all duration-300 hover:bg-card/80">
                <div className={`inline-flex p-3 rounded-xl bg-secondary/50 mb-4 ${feature.color}`}>
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">{feature.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{feature.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
