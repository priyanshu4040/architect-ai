import { motion } from "framer-motion";
import { ArrowRight, GitBranch, Layers, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-radial-gradient" />
      
      {/* Animated orbs */}
      <motion.div
        animate={{ 
          x: [0, 30, 0],
          y: [0, -20, 0],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl"
      />
      <motion.div
        animate={{ 
          x: [0, -30, 0],
          y: [0, 20, 0],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-accent/10 rounded-full blur-3xl"
      />

      <div className="container mx-auto px-4 relative z-10">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border/50 bg-secondary/30 backdrop-blur-sm mb-8"
          >
            <span className="flex h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span className="text-sm text-muted-foreground">Powered by Agentic AI</span>
          </motion.div>

          {/* Main Heading */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6"
          >
            <span className="text-foreground">Autonomous</span>{" "}
            <span className="gradient-text">Software Architecture</span>{" "}
            <span className="text-foreground">Planning</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-8"
          >
            AI-powered architecture planning and evolution. Two intelligent agents collaborate 
            to analyze, plan, and optimize your software architecture—before and after development.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
          >
            <Button variant="hero" size="xl" asChild>
              <Link to="/setup?mode=greenfield">
                Start New Project
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button variant="hero-outline" size="xl" asChild>
              <Link to="/setup?mode=brownfield">
                Analyze Existing Project
              </Link>
            </Button>
          </motion.div>

          {/* Feature Pills */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary/50 border border-border/50">
              <Layers className="h-4 w-4 text-primary" />
              <span className="text-sm text-foreground">Greenfield Planning</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary/50 border border-border/50">
              <GitBranch className="h-4 w-4 text-accent" />
              <span className="text-sm text-foreground">Brownfield Analysis</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary/50 border border-border/50">
              <Zap className="h-4 w-4 text-warning" />
              <span className="text-sm text-foreground">Real-time Collaboration</span>
            </div>
          </motion.div>
        </div>

        {/* Architecture Preview Card */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
          className="mt-20 max-w-5xl mx-auto"
        >
          <div className="glass-card glow-border p-1">
            <div className="bg-card rounded-lg overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border/50">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-destructive/70" />
                  <div className="w-3 h-3 rounded-full bg-warning/70" />
                  <div className="w-3 h-3 rounded-full bg-success/70" />
                </div>
                <span className="text-xs text-muted-foreground ml-2">Architecture Analysis Dashboard</span>
              </div>
              <div className="p-6">
                <ArchitecturePreview />
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function ArchitecturePreview() {
  const layers = [
    { name: "Presentation Layer", color: "from-primary/20 to-primary/5", items: ["React UI", "API Gateway", "Auth"] },
    { name: "Business Logic", color: "from-accent/20 to-accent/5", items: ["Services", "Validators", "Processors"] },
    { name: "Data Access", color: "from-success/20 to-success/5", items: ["Repositories", "Cache", "ORM"] },
    { name: "Infrastructure", color: "from-warning/20 to-warning/5", items: ["Database", "Message Queue", "Storage"] },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {layers.map((layer, index) => (
        <motion.div
          key={layer.name}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.6 + index * 0.1 }}
          className={`p-4 rounded-lg bg-gradient-to-b ${layer.color} border border-border/30`}
        >
          <h4 className="text-sm font-medium text-foreground mb-3">{layer.name}</h4>
          <div className="space-y-2">
            {layer.items.map((item) => (
              <div
                key={item}
                className="text-xs text-muted-foreground bg-background/50 px-2 py-1.5 rounded"
              >
                {item}
              </div>
            ))}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
