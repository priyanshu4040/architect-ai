"""
D3.js Dependency Graph Generator.

Converts the Mermaid diagram block from the LLM's architecture_plan output
into an interactive D3.js force-directed graph rendered in the browser.
"""

import json
import os
import re
import webbrowser


def parse_mermaid_to_graph(text: str) -> dict:
    """
    Extracts a Mermaid graph TD block from LLM output and parses it into
    D3.js-compatible {nodes, edges} format.

    Handles patterns like:
        A --> B
        A -->|label| B
        A["Label"] -->|label| B["Label"]
        A[Label] --> B[Label]
    """
    nodes = {}
    edges = []

    # Extract mermaid block
    mermaid_match = re.search(r"```mermaid(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if not mermaid_match:
        return {"nodes": [], "edges": [], "error": "No Mermaid diagram found in architecture plan."}

    mermaid_code = mermaid_match.group(1).strip()

    # Step 1: collect node labels — matches A["Label"] or A[Label]
    node_label_re = re.compile(r'(\w+)\[["\'"]?([^"\'\]\[]+)["\'"]?\]')

    def get_or_create(node_id: str, hint_label: str = None):
        label = hint_label.strip() if hint_label else node_id
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label}
        elif hint_label:
            nodes[node_id]["label"] = label

    for line in mermaid_code.splitlines():
        line = line.strip()
        if not line or line.lower().startswith(("graph", "subgraph", "end", "%%")):
            continue

        # Collect node label hints from this line BEFORE stripping
        for nid, nlabel in node_label_re.findall(line):
            get_or_create(nid, nlabel)

        # Strip ALL bracket groups so A["My Class"] --> B["Base"] becomes A --> B
        clean = re.sub(r'\[.*?\]', '', line)  # remove [...]
        # Also strip trailing > that some LLMs emit after |label|>
        clean = clean.replace("|>", "|").replace("->|", "--|")

        # Match edges: SRC -->|label| TGT  or  SRC --> TGT
        edge_match = re.match(
            r'\s*(\w+)\s*'                                  # source
            r'(?:-->|==>|==|-.-?>?|--[->]|---)\s*'          # arrow (tolerant)
            r'(?:\|([^|]*)\|>?\s*)?'                        # optional |label| or |label|>
            r'(\w+)',                                        # target
            clean
        )
        if edge_match:
            src   = edge_match.group(1)
            label = (edge_match.group(2) or "uses").strip()
            tgt   = edge_match.group(3)
            get_or_create(src)
            get_or_create(tgt)
            edges.append({"source": src, "target": tgt, "label": label})

    return {"nodes": list(nodes.values()), "edges": edges}


def parse_text_to_graph(text: str, *, max_nodes: int = 60) -> dict:
    """
    Fallback graph parser when the LLM didn't emit a Mermaid block.

    Produces a best-effort {nodes, edges} payload that matches the frontend
    `AnalyzeResponse.graph` format so the UI doesn't fall back to dummy data.

    Strategy:
    - Extract likely component/class tokens (CamelCase, snake_case with suffixes)
    - Build nodes (type="class") and (optionally) edges from simple arrow patterns
    """
    if not text:
        return {"nodes": [], "edges": [], "error": "Empty architecture plan text."}

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(label: str) -> str:
        # Stable, compact IDs for frontend graph
        node_id = re.sub(r"[^a-zA-Z0-9_]+", "_", label).strip("_")
        if not node_id:
            node_id = f"node_{len(nodes) + 1}"
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": label,
                "type": "class",
                "description": _smart_label(label),
                "group": 2,
            }
        return node_id

    # 1) Extract likely component names
    # Prefer explicit lists like `ClassName`, `UserService`, `order_service`, etc.
    token_re = re.compile(
        r"\b("
        r"[A-Z][A-Za-z0-9]{2,}"  # CamelCase-ish
        r"|[a-z][a-z0-9_]{2,}(?:_service|_controller|_repo|_repository|_client|_gateway|_worker|_handler)"
        r")\b"
    )
    candidates = token_re.findall(text)

    # De-dupe while preserving order
    seen = set()
    ordered: list[str] = []
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        ordered.append(c)
        if len(ordered) >= max_nodes:
            break

    for label in ordered:
        add_node(label)

    # 2) Extract simple relationship hints like "A -> B", "A --> B", "A => B"
    rel_re = re.compile(r"\b([A-Za-z][A-Za-z0-9_]{2,})\s*(-{1,3}|={1,2})>\s*([A-Za-z][A-Za-z0-9_]{2,})\b")
    for src_label, _, tgt_label in rel_re.findall(text):
        if len(edges) > 200:
            break
        src = add_node(src_label)
        tgt = add_node(tgt_label)
        if src != tgt:
            edges.append({"source": src, "target": tgt, "label": "uses"})

    if not nodes:
        return {"nodes": [], "edges": [], "error": "No components could be extracted from architecture plan text."}

    return {"nodes": list(nodes.values()), "edges": edges}


def parse_ast_summary_to_graph(ast_summary: str) -> dict:
    """
    Builds D3.js-compatible graph data from the actual AST summary text generated
    by `agents/ast_parser.py`. This uses REAL code structure — no hallucination.

    AST summary format:
        [FILE] path/to/file.py
          Classes: MyClass, SubClass (Inherits: MyClass)
    """
    nodes = {}
    edges = []
    current_file = None

    def add_node(node_id: str, label: str, ntype: str, group: int):
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "type": ntype,
                              "description": ntype.capitalize(), "group": group}

    for line in ast_summary.splitlines():
        line = line.strip()

        # New file section
        if line.startswith("[FILE]"):
            current_file = line.replace("[FILE]", "").strip()
            file_id = f"file::{current_file}"
            short = current_file.replace("\\", "/").split("/")[-1]
            add_node(file_id, short, "file", 1)

        # Classes line
        elif line.startswith("Classes:") and current_file:
            file_id = f"file::{current_file}"
            class_entries = line.replace("Classes:", "").strip().split(",")
            for entry in class_entries:
                entry = entry.strip()
                if not entry:
                    continue

                # Detect inheritance: `SubClass (Inherits: Base1, Base2)`
                inherit_match = re.match(r'(\w+)\s*\(Inherits:\s*([^)]+)\)', entry)
                if inherit_match:
                    cls_name  = inherit_match.group(1).strip()
                    bases     = [b.strip() for b in inherit_match.group(2).split(",")]
                    cls_id    = f"class::{cls_name}"
                    add_node(cls_id, cls_name, "class", 2)
                    edges.append({"source": file_id, "target": cls_id, "label": "contains"})
                    for base in bases:
                        base_id = f"class::{base}"
                        if base_id in nodes or any(
                            n["label"] == base for n in nodes.values()
                        ):
                            edges.append({"source": cls_id, "target": base_id, "label": "inherits"})
                        else:
                            add_node(base_id, base, "external", 3)
                            edges.append({"source": cls_id, "target": base_id, "label": "inherits"})
                else:
                    cls_name = re.match(r'(\w+)', entry)
                    if cls_name:
                        cls_name = cls_name.group(1)
                        cls_id   = f"class::{cls_name}"
                        add_node(cls_id, cls_name, "class", 2)
                        edges.append({"source": file_id, "target": cls_id, "label": "contains"})

        # Imports line — file -> module dependency
        elif line.startswith("Imports:") and current_file:
            file_id = f"file::{current_file}"
            imports = [i.strip() for i in line.replace("Imports:", "").split(",")]
            for imp in imports[:5]:  # limit to top 5 imports shown
                top = imp.split(".")[0]
                # Only draw edges to other known local files
                target_id = f"file::{top}.py"
                if target_id in nodes:
                    edges.append({"source": file_id, "target": target_id, "label": "imports"})

    # Attach friendly descriptions based on type
    for nid, n in nodes.items():
        if n["type"] == "file":
            n["description"] = f"Source file: {n['label']}"
        elif n["type"] == "class":
            n["description"] = "Class defined in codebase"
        elif n["type"] == "external":
            n["description"] = "External base class (inherited)"

    return {"nodes": list(nodes.values()), "edges": edges}


def generate_d3_from_ast_summary(ast_summary: str, output_file: str = "dependency_graph.html") -> str:
    """
    Builds a D3.js graph from the REAL AST summary (brownfield mode).
    This shows actual existing code structure — 100% accurate, no hallucination.
    """
    print("\nBuilding D3.js graph from real AST code structure...")
    graph_data = parse_ast_summary_to_graph(ast_summary)
    return _render_d3_html(graph_data, output_file, title="🔍 Brownfield Code Structure")


def generate_d3_graph_from_plan(architecture_plan: str, output_file: str = "dependency_graph.html") -> str:
    """
    Parses the LLM-generated architecture_plan Mermaid diagram and
    renders it as an interactive D3.js force-directed graph in the browser.
    Used in greenfield mode for the proposed new architecture.
    """
    print("\nRendering D3.js Dependency Graph from Architecture Plan...")
    graph_data = parse_mermaid_to_graph(architecture_plan)

    if "error" in graph_data:
        print(f"Warning: {graph_data['error']} Graph will be empty.")

    node_labels = [n["label"] for n in graph_data["nodes"]]
    descriptions = extract_class_descriptions(architecture_plan, node_labels)
    for node in graph_data["nodes"]:
        desc = descriptions.get(node["label"], "")
        if not desc:
            desc = _smart_label(node["label"])
        node["description"] = desc
        node["type"] = "class"

    return _render_d3_html(graph_data, output_file, title="🏗️ Architecture Dependency Graph")


def _smart_label(name: str) -> str:
    """Convert CamelCase to human-readable description.
    e.g. UserAuthService -> 'User Auth Service'
    """
    words = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    words = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', words)
    return words.strip()


def extract_class_descriptions(text: str, node_labels: list) -> dict:
    """
    Scans the architecture plan text to find short descriptions for each class.
    Tries multiple patterns common in LLM output.
    """
    descriptions = {}
    for label in node_labels:
        safe = re.escape(label)
        # Try multiple patterns:
        patterns = [
            # **ClassName** - description  or  **ClassName**: description
            rf'\*{{1,2}}{safe}\*{{0,2}}[:\s\-–]+([^\n]{{10,120}})',
            # - ClassName: description  (bullet list)
            rf'-\s*{safe}[:\s\-–]+([^\n]{{10,120}})',
            # ClassName — description or ClassName - description
            rf'{safe}[:\s\-–—]+([^\n]{{10,120}})',
            # Just grab any line mentioning the class name after a colon
            rf'{safe}.*?:\s*([^\n]{{10,120}})',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                desc = m.group(1).strip().rstrip('.').strip('*').strip()
                if len(desc) > 5:  # ignore very short matches
                    descriptions[label] = desc[:100]
                    break
    return descriptions


def _render_d3_html(graph_data: dict, output_file: str, title: str = "🏗️ Architecture Graph") -> str:
    """
    Converts graph_data {nodes, edges} into a self-contained D3.js HTML file and opens it.
    """
    graph_json = json.dumps(graph_data, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg:       #07090f; --surface:  #0e1117; --border: #1e2535;
      --text:     #cdd6f4; --muted:    #6c7086;
      --blue:     #89b4fa; --purple:   #cba6f7;
      --green:    #a6e3a1; --yellow:   #f9e2af;
      --red:      #f38ba8; --teal:     #94e2d5;
    }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html, body {{ width:100%; height:100%; overflow:hidden; background:var(--bg); font-family:'Inter',sans-serif; }}
    #header {{
      position:fixed; top:0; left:0; right:0; z-index:200; height:52px;
      background:rgba(14,17,23,0.88); backdrop-filter:blur(12px);
      border-bottom:1px solid var(--border);
      display:flex; align-items:center; padding:0 20px; gap:14px;
    }}
    #header h1 {{ font-size:15px; font-weight:600; color:var(--blue); display:flex; align-items:center; gap:7px; }}
    #subtitle {{ font-size:11px; color:var(--muted); }}
    #stats {{ margin-left:auto; display:flex; gap:10px; font-size:11px; }}
    .stat-pill {{ background:var(--border); border-radius:20px; padding:3px 10px; color:var(--text); }}
    #legend {{ display:flex; gap:12px; font-size:11px; align-items:center; border-left:1px solid var(--border); padding-left:14px; }}
    .leg {{ display:flex; align-items:center; gap:5px; color:var(--muted); }}
    .leg-line {{ width:18px; height:2px; border-radius:2px; }}
    svg {{ width:100%; height:calc(100vh - 52px); margin-top:52px; cursor:grab; }}
    svg:active {{ cursor:grabbing; }}
    .node-group {{ cursor:pointer; }}
    .node-bg {{ fill:var(--surface); stroke:var(--border); stroke-width:1.5;
                filter:drop-shadow(0 4px 12px rgba(0,0,0,.5)); }}
    .node-name {{ font-size:12px; font-weight:600; fill:var(--text); dominant-baseline:middle; text-anchor:middle; }}
    .node-desc {{ font-size:9px; fill:var(--muted); dominant-baseline:middle; text-anchor:middle; }}
    .link {{ fill:none; stroke-width:1.5; stroke-opacity:0.65; }}
    .link-inherits {{ stroke:var(--purple); stroke-dasharray:5,3; }}
    .link-uses, .link-contains {{ stroke:var(--green); }}
    .link-creates  {{ stroke:var(--yellow); }}
    .link-calls, .link-imports {{ stroke:var(--teal); }}
    .link-default  {{ stroke:var(--blue); stroke-opacity:0.4; }}
    .link-label-bg  {{ fill:var(--bg); opacity:0.85; }}
    .link-label-txt {{ font-size:9px; fill:var(--muted); dominant-baseline:middle; text-anchor:middle; pointer-events:none; }}
    #tooltip {{
      position:fixed; z-index:999; pointer-events:none; display:none;
      background:var(--surface); border:1px solid var(--border);
      border-radius:10px; padding:12px 15px; max-width:260px;
      box-shadow:0 8px 32px rgba(0,0,0,.6);
    }}
    .tip-name {{ font-size:13px; font-weight:600; color:var(--blue); margin-bottom:4px; }}
    .tip-type {{ font-size:10px; color:var(--muted); margin-bottom:6px; }}
    .tip-desc {{ font-size:11px; color:var(--text); line-height:1.5; }}
    #empty-msg {{
      display:none; position:fixed; top:50%; left:50%;
      transform:translate(-50%,-50%); text-align:center; color:var(--muted);
    }}
  </style>
</head>
<body>
  <div id="header">
    <h1>{title}</h1>
    <div id="subtitle">scroll to zoom · drag to pan · drag nodes to rearrange</div>
    <div id="stats">
      <span class="stat-pill" id="node-count">0 nodes</span>
      <span class="stat-pill" id="edge-count">0 edges</span>
    </div>
    <div id="legend">
      <span class="leg"><span class="leg-line" style="background:var(--green)"></span>uses / contains</span>
      <span class="leg"><span class="leg-line" style="background:var(--purple)"></span>inherits</span>
      <span class="leg"><span class="leg-line" style="background:var(--teal)"></span>imports / calls</span>
      <span class="leg"><span class="leg-line" style="background:var(--yellow)"></span>creates</span>
    </div>
  </div>
  <svg id="graph-svg"></svg>
  <div id="tooltip">
    <div class="tip-name" id="tip-name"></div>
    <div class="tip-type" id="tip-type"></div>
    <div class="tip-desc" id="tip-desc"></div>
  </div>
  <div id="empty-msg"><h2>⚠️ No graph data</h2><p>No diagram could be extracted.</p></div>

  <script>
  const graphData = {graph_json};
  document.getElementById("node-count").textContent = graphData.nodes.length + " nodes";
  document.getElementById("edge-count").textContent = graphData.edges.length + " edges";
  if (!graphData.nodes.length) document.getElementById("empty-msg").style.display = "block";

  const W = window.innerWidth, H = window.innerHeight - 52;
  const NW = 148, NH = 54;
  const accentColors = ["#89b4fa","#cba6f7","#a6e3a1","#f9e2af","#94e2d5","#f38ba8","#fab387"];

  const svg = d3.select("#graph-svg");
  const g   = svg.append("g");
  const tip = document.getElementById("tooltip");

  svg.call(d3.zoom().scaleExtent([0.05, 6]).on("zoom", e => g.attr("transform", e.transform)));

  const defs = svg.append("defs");
  [["arrow-inherits","#cba6f7"],["arrow-uses","#a6e3a1"],["arrow-creates","#f9e2af"],
   ["arrow-calls","#94e2d5"],["arrow-default","#89b4fa"],["arrow-contains","#a6e3a1"],
   ["arrow-imports","#94e2d5"]].forEach(([id, color]) => {{
    defs.append("marker").attr("id", id).attr("viewBox","0 -4 8 8")
        .attr("refX", 8).attr("refY", 0).attr("markerWidth", 6).attr("markerHeight", 6)
        .attr("orient","auto").append("path").attr("d","M0,-4L8,0L0,4Z").attr("fill", color);
  }});

  function edgeClass(label) {{
    const l = (label || "").toLowerCase();
    if (l.includes("inherit") || l.includes("extend")) return "inherits";
    if (l.includes("creat") || l.includes("factory")) return "creates";
    if (l.includes("call") || l.includes("api"))      return "calls";
    if (l.includes("import"))                         return "imports";
    if (l.includes("contain"))                        return "contains";
    return "uses";
  }}

  const sim = d3.forceSimulation(graphData.nodes)
    .force("link",      d3.forceLink(graphData.edges).id(d => d.id).distance(160))
    .force("charge",    d3.forceManyBody().strength(-400))
    .force("center",    d3.forceCenter(W / 2, H / 2))
    .force("x",         d3.forceX(W / 2).strength(0.08))
    .force("y",         d3.forceY(H / 2).strength(0.08))
    .force("collision", d3.forceCollide(85));

  const linkG = g.append("g");
  const link = linkG.selectAll("path")
    .data(graphData.edges).enter().append("path")
    .attr("class", d => `link link-${{edgeClass(d.label)}}`)
    .attr("marker-end", d => `url(#arrow-${{edgeClass(d.label)}})`);

  const labeledEdges = graphData.edges.filter(e => e.label && !["uses","contains"].includes(e.label));
  const linkLabelBg = linkG.selectAll(".link-label-bg").data(labeledEdges).enter()
    .append("rect").attr("class","link-label-bg").attr("width",52).attr("height",14).attr("x",-26).attr("y",-7).attr("rx",3);
  const linkLabel = linkG.selectAll(".link-label-txt").data(labeledEdges).enter()
    .append("text").attr("class","link-label-txt").text(d => d.label.length > 12 ? d.label.slice(0,11)+"…" : d.label);

  const nodeG = g.append("g");
  const node = nodeG.selectAll(".node-group")
    .data(graphData.nodes).enter().append("g").attr("class","node-group")
    .call(d3.drag()
      .on("start", (e,d) => {{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
      .on("drag",  (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
      .on("end",   (e,d) => {{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }})
    )
    .on("mouseover", (e,d) => {{
      document.getElementById("tip-name").textContent = d.label;
      document.getElementById("tip-type").textContent = d.type === "file" ? "📄 Source File" : d.type === "external" ? "⬆️ External Base" : "📦 Class";
      document.getElementById("tip-desc").textContent = d.description || "No description available.";
      tip.style.display = "block";
    }})
    .on("mousemove", e => {{ tip.style.left=(e.clientX+16)+"px"; tip.style.top=Math.min(e.clientY+12,window.innerHeight-140)+"px"; }})
    .on("mouseout", () => tip.style.display = "none");

  // Card background
  node.append("rect").attr("class","node-bg")
    .attr("x",-NW/2).attr("y",-NH/2).attr("width",NW).attr("height",NH).attr("rx",10).attr("ry",10);

  // Accent top strip
  node.append("rect")
    .attr("x",-NW/2).attr("y",-NH/2).attr("width",NW).attr("height",4).attr("rx",10).attr("ry",10)
    .attr("fill", (d,i) => d.type === "file" ? "#89b4fa" : d.type === "external" ? "#f38ba8" : accentColors[i % accentColors.length]);

  // Class name text (full label, never the letter ID)
  node.append("text").attr("class","node-name").attr("y",-7)
    .text(d => d.label.length > 17 ? d.label.slice(0,16)+"…" : d.label);

  // Role / description subtitle on card
  node.append("text").attr("class","node-desc").attr("y",11)
    .text(d => {{
      const desc = d.description || (d.type === "file" ? "Source File" : "Class");
      return desc.length > 22 ? desc.slice(0,21)+"…" : desc;
    }});

  function linkPath(d) {{
    const sx=d.source.x||0, sy=d.source.y||0, tx=d.target.x||0, ty=d.target.y||0;
    const dr = Math.hypot(tx-sx, ty-sy) * 0.55;
    return `M${{sx}},${{sy}} A${{dr}},${{dr}} 0 0,1 ${{tx}},${{ty}}`;
  }}

  sim.on("tick", () => {{
    link.attr("d", linkPath);
    linkLabelBg.attr("transform", d => `translate(${{(d.source.x+d.target.x)/2}},${{(d.source.y+d.target.y)/2}})`);
    linkLabel.attr("x", d => (d.source.x+d.target.x)/2).attr("y", d => (d.source.y+d.target.y)/2);
    node.attr("transform", d => `translate(${{d.x||0}},${{d.y||0}})`);
  }});

  window.addEventListener("resize", () => {{
    sim.force("center", d3.forceCenter(window.innerWidth/2,(window.innerHeight-52)/2));
    sim.alpha(0.3).restart();
  }});
  </script>
</body>
</html>"""

    output_path = os.path.abspath(output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Graph saved -> {output_path}")
    print("Opening in browser...")
    webbrowser.open(f"file:///{output_path}")
    return output_path
