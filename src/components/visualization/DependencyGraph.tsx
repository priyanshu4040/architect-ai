import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Server,
  Database,
  Settings,
  ChevronRight,
  ChevronDown,
  ArrowRight,
  Eye,
  EyeOff,
  Focus,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/* ── types ── */
export interface ArchNode {
  id: string;
  name: string;
  layer: "presentation" | "business" | "data" | "infrastructure";
  type: string;
  functionality: string;
  risk?: "high" | "medium" | "low";
  connections: string[];
}

interface NodePos {
  node: ArchNode;
  x: number;
  y: number;
  inDeg: number;
  outDeg: number;
}

/* ── constants ── */
const LAYER_META: Record<
  string,
  { label: string; colorClass: string; hex: string; icon: React.ElementType }
> = {
  presentation: { label: "API / Input", colorClass: "bg-primary", hex: "hsl(199 89% 48%)", icon: Server },
  business: { label: "Business Logic", colorClass: "bg-accent", hex: "hsl(185 100% 42%)", icon: FileText },
  data: { label: "Data / Models", colorClass: "bg-success", hex: "hsl(142 76% 36%)", icon: Database },
  infrastructure: { label: "Infrastructure", colorClass: "bg-warning", hex: "hsl(38 92% 50%)", icon: Settings },
};

const LAYER_ORDER: ArchNode["layer"][] = [
  "presentation",
  "business",
  "data",
  "infrastructure",
];

const CARD_W = 200;
const CARD_H = 80;
const LAYER_GAP = 280;
const NODE_GAP = 110;
const LAYER_PAD_X = 60;
const TOP_PAD = 80;

/* ── helpers ── */
function bezierPath(x1: number, y1: number, x2: number, y2: number) {
  const cx = (x1 + x2) / 2;
  return `M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`;
}

/* ── component ── */
export default function DependencyGraph({
  nodes,
  selectedNode,
  onSelectNode,
}: {
  nodes: ArchNode[];
  selectedNode: ArchNode | null;
  onSelectNode: (n: ArchNode) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  /* state */
  const [collapsedLayers, setCollapsedLayers] = useState<Set<string>>(new Set());
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showMinor, setShowMinor] = useState(true);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  /* degree maps */
  const { inDeg, outDeg } = useMemo(() => {
    const i: Record<string, number> = {};
    const o: Record<string, number> = {};
    nodes.forEach((n) => {
      o[n.id] = n.connections.length;
      n.connections.forEach((t) => {
        i[t] = (i[t] || 0) + 1;
      });
    });
    return { inDeg: i, outDeg: o };
  }, [nodes]);

  /* layout */
  const positions = useMemo<NodePos[]>(() => {
    const result: NodePos[] = [];
    LAYER_ORDER.forEach((layer, li) => {
      if (collapsedLayers.has(layer)) return;
      const layerNodes = nodes.filter((n) => n.layer === layer);
      layerNodes.forEach((n, ni) => {
        result.push({
          node: n,
          x: LAYER_PAD_X + li * LAYER_GAP,
          y: TOP_PAD + ni * NODE_GAP,
          inDeg: inDeg[n.id] || 0,
          outDeg: outDeg[n.id] || 0,
        });
      });
    });
    return result;
  }, [nodes, collapsedLayers, inDeg, outDeg]);

  /* focus set */
  const focusSet = useMemo<Set<string> | null>(() => {
    if (!focusNodeId) return null;
    const s = new Set<string>([focusNodeId]);
    const fn = nodes.find((n) => n.id === focusNodeId);
    if (fn) fn.connections.forEach((c) => s.add(c));
    nodes.forEach((n) => {
      if (n.connections.includes(focusNodeId)) s.add(n.id);
    });
    return s;
  }, [focusNodeId, nodes]);

  /* hovered connected set */
  const hoverSet = useMemo<Set<string> | null>(() => {
    if (!hoveredId) return null;
    const s = new Set<string>([hoveredId]);
    const hn = nodes.find((n) => n.id === hoveredId);
    if (hn) hn.connections.forEach((c) => s.add(c));
    nodes.forEach((n) => {
      if (n.connections.includes(hoveredId)) s.add(n.id);
    });
    return s;
  }, [hoveredId, nodes]);

  const activeSet = hoverSet || focusSet;

  /* edges */
  const edges = useMemo(() => {
    const arr: {
      key: string;
      path: string;
      src: string;
      tgt: string;
      heavy: boolean;
    }[] = [];
    positions.forEach((sp) => {
      sp.node.connections.forEach((tid) => {
        const tp = positions.find((p) => p.node.id === tid);
        if (!tp) return;
        const heavy = (inDeg[tid] || 0) >= 3 || sp.outDeg >= 3;
        if (!showMinor && !heavy) return;
        arr.push({
          key: `${sp.node.id}-${tid}`,
          path: bezierPath(
            sp.x + CARD_W,
            sp.y + CARD_H / 2,
            tp.x,
            tp.y + CARD_H / 2
          ),
          src: sp.node.id,
          tgt: tid,
          heavy,
        });
      });
    });
    return arr;
  }, [positions, showMinor, inDeg]);

  /* most connected node */
  const centralNodeId = useMemo(() => {
    let best = "";
    let max = -1;
    nodes.forEach((n) => {
      const total = (inDeg[n.id] || 0) + (outDeg[n.id] || 0);
      if (total > max) {
        max = total;
        best = n.id;
      }
    });
    return best;
  }, [nodes, inDeg, outDeg]);

  /* SVG bounds */
  const svgW = LAYER_PAD_X + LAYER_ORDER.length * LAYER_GAP + 80;
  const maxNodesInLayer = Math.max(
    ...LAYER_ORDER.map((l) => nodes.filter((n) => n.layer === l).length),
    1
  );
  const svgH = TOP_PAD + maxNodesInLayer * NODE_GAP + 40;

  /* pan & zoom handlers */
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      setZoom((z) => Math.max(0.3, Math.min(2, z - e.deltaY * 0.001)));
    } else {
      setPan((p) => ({ x: p.x - e.deltaX, y: p.y - e.deltaY }));
    }
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      setIsPanning(true);
      panStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    },
    [pan]
  );
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isPanning) return;
      setPan({
        x: panStart.current.panX + (e.clientX - panStart.current.x),
        y: panStart.current.panY + (e.clientY - panStart.current.y),
      });
    },
    [isPanning]
  );
  const handleMouseUp = useCallback(() => setIsPanning(false), []);

  const isEntryPoint = (n: ArchNode) =>
    n.name.toLowerCase().includes("main") || n.type === "gateway" || n.type === "api";

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-4">
        {/* toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowMinor((v) => !v)}
          >
            {showMinor ? (
              <EyeOff className="h-4 w-4 mr-1.5" />
            ) : (
              <Eye className="h-4 w-4 mr-1.5" />
            )}
            {showMinor ? "Hide Minor Deps" : "Show All Deps"}
          </Button>

          {focusNodeId && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFocusNodeId(null)}
            >
              <X className="h-4 w-4 mr-1.5" />
              Exit Focus
            </Button>
          )}

          <div className="ml-auto flex items-center gap-1">
            <Button variant="outline" size="sm" onClick={() => setZoom((z) => Math.max(0.3, z - 0.15))}>−</Button>
            <span className="text-xs text-muted-foreground w-12 text-center">{Math.round(zoom * 100)}%</span>
            <Button variant="outline" size="sm" onClick={() => setZoom((z) => Math.min(2, z + 0.15))}>+</Button>
            <Button variant="outline" size="sm" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}>Reset</Button>
          </div>
        </div>

        {/* layer toggles */}
        <div className="flex flex-wrap gap-2">
          {LAYER_ORDER.map((layer) => {
            const meta = LAYER_META[layer];
            const collapsed = collapsedLayers.has(layer);
            return (
              <button
                key={layer}
                onClick={() =>
                  setCollapsedLayers((prev) => {
                    const next = new Set(prev);
                    collapsed ? next.delete(layer) : next.add(layer);
                    return next;
                  })
                }
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                  collapsed
                    ? "border-border/50 text-muted-foreground opacity-60"
                    : "border-border bg-card text-foreground"
                }`}
              >
                {collapsed ? (
                  <ChevronRight className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
                <span className={`h-2.5 w-2.5 rounded-full ${meta.colorClass}`} />
                {meta.label}
              </button>
            );
          })}
        </div>

        {/* graph canvas */}
        <div
          ref={containerRef}
          className="relative w-full overflow-hidden rounded-xl border border-border bg-card/50 cursor-grab active:cursor-grabbing"
          style={{ height: "520px" }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* subtle grid */}
          <div
            className="absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage:
                "linear-gradient(hsl(var(--border)) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px)",
              backgroundSize: "40px 40px",
            }}
          />

          <svg
            ref={svgRef}
            width={svgW}
            height={svgH}
            className="absolute top-0 left-0"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "0 0",
            }}
          >
            <defs>
              <marker
                id="arrowHead"
                markerWidth="8"
                markerHeight="6"
                refX="8"
                refY="3"
                orient="auto"
              >
                <path
                  d="M0,0 L8,3 L0,6"
                  fill="none"
                  stroke="hsl(var(--muted-foreground))"
                  strokeWidth="1.5"
                />
              </marker>
              <marker
                id="arrowHeadActive"
                markerWidth="8"
                markerHeight="6"
                refX="8"
                refY="3"
                orient="auto"
              >
                <path
                  d="M0,0 L8,3 L0,6"
                  fill="none"
                  stroke="hsl(var(--primary))"
                  strokeWidth="1.5"
                />
              </marker>
            </defs>

            {/* layer labels */}
            {LAYER_ORDER.map((layer, li) => {
              if (collapsedLayers.has(layer)) return null;
              const meta = LAYER_META[layer];
              return (
                <text
                  key={layer}
                  x={LAYER_PAD_X + li * LAYER_GAP + CARD_W / 2}
                  y={30}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[11px] font-semibold uppercase tracking-wider"
                >
                  {meta.label}
                </text>
              );
            })}

            {/* edges */}
            {edges.map((e) => {
              const isActive =
                activeSet && (activeSet.has(e.src) && activeSet.has(e.tgt));
              const dimmed = activeSet && !isActive;
              return (
                <motion.path
                  key={e.key}
                  d={e.path}
                  fill="none"
                  stroke={
                    isActive
                      ? "hsl(var(--primary))"
                      : "hsl(var(--muted-foreground))"
                  }
                  strokeWidth={isActive ? 2.5 : e.heavy ? 1.8 : 1}
                  strokeDasharray={e.heavy || isActive ? undefined : "4 3"}
                  opacity={dimmed ? 0.12 : isActive ? 1 : 0.35}
                  markerEnd={isActive ? "url(#arrowHeadActive)" : "url(#arrowHead)"}
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                />
              );
            })}

            {/* node cards as foreignObject */}
            {positions.map((pos, idx) => {
              const { node, x, y, inDeg: iDeg, outDeg: oDeg } = pos;
              const meta = LAYER_META[node.layer];
              const Icon = meta.icon;
              const isSelected = selectedNode?.id === node.id;
              const isCentral = node.id === centralNodeId;
              const isEntry = isEntryPoint(node);
              const dimmed = activeSet && !activeSet.has(node.id);

              return (
                <motion.g
                  key={node.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: dimmed ? 0.15 : 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                >
                  <foreignObject x={x} y={y} width={CARD_W} height={CARD_H}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div
                          onClick={() => onSelectNode(node)}
                          onDoubleClick={() =>
                            setFocusNodeId((prev) =>
                              prev === node.id ? null : node.id
                            )
                          }
                          onMouseEnter={() => setHoveredId(node.id)}
                          onMouseLeave={() => setHoveredId(null)}
                          className={`
                            h-full flex items-start gap-2 p-3 rounded-xl border-2 cursor-pointer
                            transition-all duration-200 select-none
                            bg-card text-card-foreground
                            ${
                              isSelected
                                ? "border-primary shadow-lg shadow-primary/20 scale-[1.03]"
                                : isCentral
                                ? "border-primary/40 shadow-md"
                                : "border-border/60 shadow-sm hover:shadow-md hover:border-primary/30 hover:-translate-y-0.5"
                            }
                          `}
                        >
                          {/* icon */}
                          <div
                            className={`flex-shrink-0 mt-0.5 p-1.5 rounded-lg ${meta.colorClass}/15`}
                          >
                            <Icon
                              className="h-4 w-4"
                              style={{ color: meta.hex }}
                            />
                          </div>

                          <div className="min-w-0 flex-1">
                            {/* name */}
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-semibold truncate text-foreground">
                                {node.name}
                              </span>
                              {isEntry && (
                                <span className="text-[9px] px-1 py-0.5 rounded bg-primary/20 text-primary font-medium">
                                  entry
                                </span>
                              )}
                            </div>
                            {/* layer badge + degree */}
                            <div className="flex items-center gap-1.5 mt-1">
                              <span
                                className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium text-primary-foreground ${meta.colorClass}`}
                              >
                                {meta.label}
                              </span>
                              <span className="text-[9px] text-muted-foreground">
                                ↓{iDeg} ↑{oDeg}
                              </span>
                            </div>
                          </div>

                          {/* risk dot */}
                          {node.risk && (
                            <span
                              className={`absolute -top-1 -right-1 h-3 w-3 rounded-full border-2 border-card ${
                                node.risk === "high"
                                  ? "bg-destructive"
                                  : node.risk === "medium"
                                  ? "bg-warning"
                                  : "bg-success"
                              }`}
                            />
                          )}
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="max-w-[240px] space-y-1">
                        <p className="font-semibold text-xs">{node.name}</p>
                        <p className="text-[10px] text-muted-foreground">{node.functionality}</p>
                        <p className="text-[10px]">
                          <span className="text-muted-foreground">Type:</span>{" "}
                          <span className="capitalize">{node.type}</span>
                        </p>
                        {node.connections.length > 0 && (
                          <p className="text-[10px]">
                            <span className="text-muted-foreground">Depends on:</span>{" "}
                            {node.connections
                              .map((c) => nodes.find((n) => n.id === c)?.name || c)
                              .join(", ")}
                          </p>
                        )}
                        <p className="text-[10px] text-muted-foreground italic">
                          Double-click to focus
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </foreignObject>
                </motion.g>
              );
            })}
          </svg>
        </div>

        {/* legend */}
        <div className="flex flex-wrap justify-center gap-4 pt-2">
          {LAYER_ORDER.map((layer) => {
            const meta = LAYER_META[layer];
            return (
              <div key={layer} className="flex items-center gap-1.5">
                <span className={`h-2.5 w-2.5 rounded-full ${meta.colorClass}`} />
                <span className="text-xs text-muted-foreground">{meta.label}</span>
              </div>
            );
          })}
          <div className="flex items-center gap-1.5">
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Dependency flow</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Focus className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Double-click to focus</span>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
