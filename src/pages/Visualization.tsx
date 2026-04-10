import { useState } from "react";
import { motion } from "framer-motion";
import { 
  AlertTriangle, 
  ChevronDown, 
  ChevronUp, 
  Layers, 
  Link2, 
  Maximize2,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { Link } from "react-router-dom";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { loadLastResult } from "@/lib/api";

interface ArchNode {
  id: string;
  name: string;
  layer: string;
  type: string;
  risk?: "high" | "medium" | "low";
  connections: string[];
}

function graphToArchNodes(graph: { nodes: { id: string; label: string; type?: string | null }[]; edges: { source: string; target: string }[] }): ArchNode[] {
  const byId = new Map<string, ArchNode>();
  for (const n of graph.nodes || []) {
    // Best-effort layer/type mapping from backend graph
    const t = (n.type || "component").toString();
    const layer =
      t.includes("file") ? "presentation" :
      t.includes("class") ? "business" :
      t.includes("external") ? "infrastructure" :
      "business";
    byId.set(n.id, {
      id: n.id,
      name: n.label || n.id,
      layer,
      type: t,
      connections: [],
    });
  }
  for (const e of graph.edges || []) {
    const src = byId.get(e.source);
    if (src) src.connections.push(e.target);
  }
  return Array.from(byId.values());
}

const mockArchitecture: ArchNode[] = [
  // Presentation Layer
  { id: "p1", name: "React UI", layer: "presentation", type: "frontend", connections: ["b1", "b2"] },
  { id: "p2", name: "API Gateway", layer: "presentation", type: "gateway", connections: ["b1", "b2", "b3"] },
  { id: "p3", name: "Auth Service", layer: "presentation", type: "auth", connections: ["b2", "d1"] },
  
  // Business Logic
  { id: "b1", name: "Order Service", layer: "business", type: "service", risk: "high", connections: ["d1", "d2"] },
  { id: "b2", name: "User Service", layer: "business", type: "service", connections: ["d1"] },
  { id: "b3", name: "Notification", layer: "business", type: "service", connections: ["i1"] },
  { id: "b4", name: "Analytics", layer: "business", type: "service", risk: "medium", connections: ["d2", "d3"] },
  
  // Data Layer
  { id: "d1", name: "User DB", layer: "data", type: "database", connections: [] },
  { id: "d2", name: "Order DB", layer: "data", type: "database", risk: "high", connections: [] },
  { id: "d3", name: "Redis Cache", layer: "data", type: "cache", connections: [] },
  
  // Infrastructure
  { id: "i1", name: "Message Queue", layer: "infrastructure", type: "queue", connections: [] },
  { id: "i2", name: "File Storage", layer: "infrastructure", type: "storage", connections: [] },
];

const layers = [
  { id: "presentation", name: "Presentation Layer", color: "from-primary/30 to-primary/10" },
  { id: "business", name: "Business Logic Layer", color: "from-accent/30 to-accent/10" },
  { id: "data", name: "Data Access Layer", color: "from-success/30 to-success/10" },
  { id: "infrastructure", name: "Infrastructure Layer", color: "from-warning/30 to-warning/10" },
];

export default function Visualization() {
  const last = loadLastResult();
  const backendNodes =
    last?.graph?.nodes?.length ? graphToArchNodes(last.graph as any) : null;
  const arch = backendNodes || mockArchitecture;

  const [selectedNode, setSelectedNode] = useState<ArchNode | null>(null);
  const [zoom, setZoom] = useState(100);
  const [expandedLayers, setExpandedLayers] = useState<string[]>(layers.map(l => l.id));

  const toggleLayer = (layerId: string) => {
    setExpandedLayers(prev => 
      prev.includes(layerId) 
        ? prev.filter(id => id !== layerId)
        : [...prev, layerId]
    );
  };

  const getNodesByLayer = (layerId: string) => 
    arch.filter(node => node.layer === layerId);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-16">
        <div className="container mx-auto px-4">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8"
          >
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold mb-2">
                <span className="text-foreground">Architecture </span>
                <span className="gradient-text">Visualization</span>
              </h1>
              <p className="text-muted-foreground">
                Interactive view of your system architecture
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="icon"
                onClick={() => setZoom(Math.max(50, zoom - 10))}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground w-12 text-center">{zoom}%</span>
              <Button 
                variant="outline" 
                size="icon"
                onClick={() => setZoom(Math.min(150, zoom + 10))}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <Maximize2 className="h-4 w-4" />
              </Button>
            </div>
          </motion.div>

          <Tabs defaultValue="layers" className="space-y-8">
            <TabsList className="bg-secondary/50">
              <TabsTrigger value="layers">Layered View</TabsTrigger>
              <TabsTrigger value="dependencies">Dependency Graph</TabsTrigger>
            </TabsList>

            {/* Layered Architecture View */}
            <TabsContent value="layers">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Main Visualization */}
                <div className="lg:col-span-3 glass-card p-6 overflow-auto">
                  <div 
                    className="space-y-4 min-w-[600px] transition-transform"
                    style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
                  >
                    {layers.map((layer) => (
                      <motion.div
                        key={layer.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`rounded-xl border border-border/50 bg-gradient-to-r ${layer.color} overflow-hidden`}
                      >
                        <button
                          onClick={() => toggleLayer(layer.id)}
                          className="w-full flex items-center justify-between p-4 hover:bg-background/5 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <Layers className="h-5 w-5 text-foreground" />
                            <span className="font-medium text-foreground">{layer.name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({getNodesByLayer(layer.id).length} components)
                        </span>
                          </div>
                          {expandedLayers.includes(layer.id) ? (
                            <ChevronUp className="h-5 w-5 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-5 w-5 text-muted-foreground" />
                          )}
                        </button>
                        
                        {expandedLayers.includes(layer.id) && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="p-4 pt-0"
                          >
                            <div className="flex flex-wrap gap-3">
                              {getNodesByLayer(layer.id).map((node) => (
                                <button
                                  key={node.id}
                                  onClick={() => setSelectedNode(node)}
                                  className={`group relative px-4 py-3 rounded-lg border-2 transition-all ${
                                    selectedNode?.id === node.id
                                      ? "border-primary bg-primary/10"
                                      : "border-border/50 bg-card/80 hover:border-primary/50"
                                  }`}
                                >
                                  {node.risk && (
                                    <span className={`absolute -top-1 -right-1 h-3 w-3 rounded-full ${
                                      node.risk === "high" ? "bg-destructive" :
                                      node.risk === "medium" ? "bg-warning" : "bg-success"
                                    }`} />
                                  )}
                                  <span className="text-sm font-medium text-foreground">{node.name}</span>
                                  <span className="block text-xs text-muted-foreground mt-0.5">{node.type}</span>
                                </button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </div>

                {/* Details Panel */}
                <div className="glass-card p-6">
                  <h3 className="text-lg font-semibold text-foreground mb-4">Component Details</h3>
                  
                  {selectedNode ? (
                    <motion.div
                      key={selectedNode.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="space-y-4"
                    >
                      <div>
                        <p className="text-sm text-muted-foreground">Name</p>
                        <p className="text-foreground font-medium">{selectedNode.name}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Layer</p>
                        <p className="text-foreground capitalize">{selectedNode.layer}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Type</p>
                        <p className="text-foreground capitalize">{selectedNode.type}</p>
                      </div>
                      {selectedNode.risk && (
                        <div>
                          <p className="text-sm text-muted-foreground">Risk Level</p>
                          <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${
                            selectedNode.risk === "high" ? "bg-destructive/20 text-destructive" :
                            selectedNode.risk === "medium" ? "bg-warning/20 text-warning" :
                            "bg-success/20 text-success"
                          }`}>
                            <AlertTriangle className="h-3 w-3" />
                            {selectedNode.risk.charAt(0).toUpperCase() + selectedNode.risk.slice(1)}
                          </div>
                        </div>
                      )}
                      <div>
                        <p className="text-sm text-muted-foreground mb-2">Connections</p>
                        <div className="space-y-1">
                          {selectedNode.connections.length > 0 ? (
                            selectedNode.connections.map((connId) => {
                              const connected = arch.find(n => n.id === connId);
                              return connected ? (
                                <div key={connId} className="flex items-center gap-2 text-sm">
                                  <Link2 className="h-3 w-3 text-primary" />
                                  <span className="text-foreground">{connected.name}</span>
                                </div>
                              ) : null;
                            })
                          ) : (
                            <p className="text-sm text-muted-foreground">No outbound connections</p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Select a component to view details
                    </p>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Dependency Graph View */}
            <TabsContent value="dependencies">
              <div className="glass-card p-8">
                <DependencyGraph nodes={arch} selectedNode={selectedNode} onSelectNode={setSelectedNode} />
              </div>
            </TabsContent>
          </Tabs>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex justify-center gap-4 mt-8"
          >
            <Button variant="hero" asChild>
              <Link to="/results">View Full Results</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/reports">Download Report</Link>
            </Button>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function DependencyGraph({ 
  nodes, 
  selectedNode, 
  onSelectNode 
}: { 
  nodes: ArchNode[]; 
  selectedNode: ArchNode | null;
  onSelectNode: (node: ArchNode) => void;
}) {
  // Calculate positions for nodes in a circular layout
  const centerX = 400;
  const centerY = 300;
  const radius = 220;
  
  const nodePositions = nodes.map((node, index) => {
    const angle = (2 * Math.PI * index) / nodes.length - Math.PI / 2;
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  const getNodePos = (id: string) => nodePositions.find(n => n.id === id);

  return (
    <div className="relative w-full overflow-auto">
      <svg width="800" height="600" className="mx-auto">
        {/* Connection Lines */}
        {nodePositions.map(node => 
          node.connections.map(targetId => {
            const target = getNodePos(targetId);
            if (!target) return null;
            const isHighlighted = selectedNode?.id === node.id || selectedNode?.id === targetId;
            return (
              <motion.line
                key={`${node.id}-${targetId}`}
                x1={node.x}
                y1={node.y}
                x2={target.x}
                y2={target.y}
                className={isHighlighted ? "node-line-active" : "node-line"}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, delay: 0.5 }}
              />
            );
          })
        )}

        {/* Nodes */}
        {nodePositions.map((node, index) => {
          const layerColors: Record<string, string> = {
            presentation: "#0ea5e9",
            business: "#14b8a6",
            data: "#22c55e",
            infrastructure: "#f59e0b",
          };
          const color = layerColors[node.layer] || "#64748b";
          const isSelected = selectedNode?.id === node.id;

          return (
            <motion.g
              key={node.id}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => onSelectNode(node)}
              className="cursor-pointer"
            >
              {/* Glow effect for selected */}
              {isSelected && (
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="35"
                  fill={color}
                  opacity="0.3"
                  className="animate-pulse"
                />
              )}
              
              {/* Node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r="28"
                fill={isSelected ? color : `${color}33`}
                stroke={color}
                strokeWidth={isSelected ? 3 : 2}
                className="transition-all duration-200"
              />
              
              {/* Risk indicator */}
              {node.risk && (
                <circle
                  cx={node.x + 20}
                  cy={node.y - 20}
                  r="6"
                  fill={node.risk === "high" ? "#ef4444" : node.risk === "medium" ? "#f59e0b" : "#22c55e"}
                />
              )}
              
              {/* Label */}
              <text
                x={node.x}
                y={node.y + 45}
                textAnchor="middle"
                className="fill-foreground text-xs font-medium"
              >
                {node.name}
              </text>
            </motion.g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-6 mt-4">
        {layers.map(layer => {
          const layerColors: Record<string, string> = {
            presentation: "bg-primary",
            business: "bg-accent",
            data: "bg-success",
            infrastructure: "bg-warning",
          };
          return (
            <div key={layer.id} className="flex items-center gap-2">
              <div className={`h-3 w-3 rounded-full ${layerColors[layer.id]}`} />
              <span className="text-xs text-muted-foreground">{layer.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
