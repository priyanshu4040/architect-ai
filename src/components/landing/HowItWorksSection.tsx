import { motion } from "framer-motion";
import { FileCode, GitBranch, Layers, Upload, Zap } from "lucide-react";

const greenfieldSteps = [
  {
    icon: FileCode,
    title: "Define Requirements",
    description: "Enter functional and non-functional requirements for your new project",
  },
  {
    icon: Zap,
    title: "Agent Analysis",
    description: "AI agents collaborate to analyze requirements and constraints",
  },
  {
    icon: Layers,
    title: "Architecture Plan",
    description: "Receive a comprehensive architecture with patterns and justifications",
  },
];

const brownfieldSteps = [
  {
    icon: Upload,
    title: "Upload Codebase",
    description: "Provide your existing code via file upload or repository link",
  },
  {
    icon: GitBranch,
    title: "Deep Analysis",
    description: "Analysis agent examines structure, dependencies, and patterns",
  },
  {
    icon: Layers,
    title: "Evolution Roadmap",
    description: "Get recommendations for improvements and modernization paths",
  },
];

export function HowItWorksSection() {
  return (
    <section className="py-24 relative bg-secondary/20">
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
            <span className="text-foreground">Two Modes, </span>
            <span className="gradient-text">One Powerful Workflow</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Whether you're starting from scratch or evolving an existing system, 
            our agents adapt to your needs.
          </p>
        </motion.div>

        {/* Modes Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Greenfield Mode */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="glass-card p-8"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/50">
                <Layers className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-foreground">Greenfield Mode</h3>
                <p className="text-sm text-muted-foreground">For new projects</p>
              </div>
            </div>

            <div className="space-y-4">
              {greenfieldSteps.map((step, index) => (
                <div key={step.title} className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <step.icon className="h-5 w-5" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-primary">Step {index + 1}</span>
                    </div>
                    <h4 className="text-sm font-medium text-foreground">{step.title}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Brownfield Mode */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="glass-card p-8"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-accent/50">
                <GitBranch className="h-6 w-6 text-accent-foreground" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-foreground">Brownfield Mode</h3>
                <p className="text-sm text-muted-foreground">For existing projects</p>
              </div>
            </div>

            <div className="space-y-4">
              {brownfieldSteps.map((step, index) => (
                <div key={step.title} className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
                      <step.icon className="h-5 w-5" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-accent">Step {index + 1}</span>
                    </div>
                    <h4 className="text-sm font-medium text-foreground">{step.title}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
