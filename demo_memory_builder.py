"""
Demo Memory Builder
====================
Standalone script — NOT connected to the agent pipeline.

Reads uploaded zip files, parses their code structure using the
project's AST parser, and writes `demo_memory.json` — a rich,
human-readable representation of what the ChromaDB memory
system would store after training on these codebases.

Usage:
    python demo_memory_builder.py

Output:
    demo_memory.json   — the demo memory knowledge base
"""

import ast
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ZIP_FILES = [
    SCRIPT_DIR / "DesignPatterns-master.zip",
    SCRIPT_DIR / "DesignPatternsJava9-master.zip",
    SCRIPT_DIR / "refactoring-code_smells-design_patterns-main.zip",
]
OUTPUT_FILE = SCRIPT_DIR / "demo_memory.json"

# Extensions to parse
SUPPORTED_EXTS = {".py", ".java", ".ts", ".tsx", ".js", ".jsx", ".go", ".cs", ".rb", ".php"}

# Directories to always skip
SKIP_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__", ".git",
    "dist", "build", ".next", "coverage", ".cache", "vendor", "target",
}

# Max files per zip to keep demo lightweight
MAX_FILES_PER_ZIP = 60

# ─── AST Parsing (Python only — high precision) ───────────────────────────────

def _parse_python(filepath: str) -> dict:
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=filepath)
    except Exception:
        return {}

    imports, classes, functions = [], [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    imports.append(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.ClassDef):
            bases = [
                (b.id if isinstance(b, ast.Name) else b.attr)
                for b in node.bases
                if isinstance(b, (ast.Name, ast.Attribute))
            ]
            classes.append(f"{node.name}({', '.join(bases)})" if bases else node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    return {"imports": imports[:15], "classes": classes[:25], "functions": functions[:25]}


# ─── Regex parser (Java / TS / JS / Go / C# etc.) ────────────────────────────

def _parse_generic(filepath: str, lang: str) -> dict:
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}

    imports, classes, functions = [], [], []

    if lang == "java":
        imports = re.findall(r"^import\s+([\w.]+);", source, re.MULTILINE)[:15]
        for m in re.finditer(
            r"\b(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?",
            source,
        ):
            classes.append(f"{m.group(1)} extends {m.group(2)}" if m.group(2) else m.group(1))
        for m in re.finditer(r"\binterface\s+(\w+)", source):
            classes.append(f"{m.group(1)} [interface]")
        functions = re.findall(
            r"\b(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(", source
        )[:25]

    elif lang in ("ts", "tsx", "js", "jsx"):
        imports = re.findall(r"""import\s+(?:.*?from\s+)?['"]([^'"]+)['"]""", source)[:15]
        for m in re.finditer(r"\bclass\s+(\w+)(?:\s+extends\s+(\w+))?", source):
            classes.append(f"{m.group(1)} extends {m.group(2)}" if m.group(2) else m.group(1))
        functions = re.findall(
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", source
        )[:25]

    elif lang == "go":
        imports = re.findall(r'"([\w./]+)"', source)[:15]
        classes = [f"{m.group(1)} [struct]" for m in re.finditer(r"\btype\s+(\w+)\s+struct\b", source)]
        functions = re.findall(r"\bfunc\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", source)[:25]

    elif lang in ("cs", "csharp"):
        imports = re.findall(r"^using\s+([\w.]+);", source, re.MULTILINE)[:15]
        classes = re.findall(
            r"\b(?:public|private|internal|protected)?\s*(?:abstract\s+|sealed\s+)?class\s+(\w+)", source
        )[:25]
        functions = re.findall(
            r"\b(?:public|private|protected|internal)\s+(?:static\s+|async\s+)?[\w<>\[\]]+\s+(\w+)\s*\(", source
        )[:25]

    return {
        "imports": list(dict.fromkeys(imports))[:15],
        "classes": list(dict.fromkeys(classes))[:25],
        "functions": list(dict.fromkeys(functions))[:25],
    }


def _parse_file(filepath: str) -> dict | None:
    ext = Path(filepath).suffix.lower()
    lang_map = {
        ".py": "python", ".java": "java",
        ".ts": "ts", ".tsx": "tsx", ".js": "js", ".jsx": "jsx",
        ".go": "go", ".cs": "csharp",
    }
    lang = lang_map.get(ext)
    if not lang:
        return None
    data = _parse_python(filepath) if lang == "python" else _parse_generic(filepath, lang)
    if not data or not any(data.values()):
        return None
    return {**data, "lang": lang}


# ─── Design Pattern Detector ─────────────────────────────────────────────────

_PATTERN_SIGNALS: list[tuple[str, list[str]]] = [
    ("Singleton",       ["singleton", "getInstance", "instance", "_instance"]),
    ("Factory",         ["factory", "create", "Factory", "Creator", "createProduct"]),
    ("Abstract Factory",["AbstractFactory", "ConcreteFactory", "createButton", "createCheckbox"]),
    ("Builder",         ["Builder", "build", "setName", "setAge", "Director"]),
    ("Prototype",       ["clone", "Prototype", "cloneMe", "copy"]),
    ("Adapter",         ["Adapter", "adaptee", "Adaptee", "adapt", "Target"]),
    ("Decorator",       ["Decorator", "ConcreteDecorator", "wrappee", "Wrapper"]),
    ("Facade",          ["Facade", "subsystem", "SubSystem"]),
    ("Proxy",           ["Proxy", "RealSubject", "ProxyService"]),
    ("Observer",        ["Observer", "Subject", "notify", "subscribe", "listener", "EventEmitter"]),
    ("Strategy",        ["Strategy", "ConcreteStrategy", "setStrategy", "algorithm"]),
    ("Command",         ["Command", "Invoker", "Receiver", "execute", "undo"]),
    ("Iterator",        ["Iterator", "hasNext", "next", "Iterable"]),
    ("State",           ["State", "ConcreteState", "setState", "handle"]),
    ("Template Method", ["templateMethod", "AbstractClass", "primitiveOperation"]),
    ("Composite",       ["Composite", "Component", "Leaf", "add", "remove", "getChildren"]),
    ("Chain of Resp.",  ["Handler", "nextHandler", "setNext", "handleRequest"]),
    ("Visitor",         ["Visitor", "ConcreteVisitor", "accept", "visit"]),
    ("Mediator",        ["Mediator", "Colleague", "notify", "ConcreteMediator"]),
    ("Flyweight",       ["Flyweight", "FlyweightFactory", "getCharacter", "intrinsic"]),
    ("Bridge",          ["Abstraction", "Implementor", "RefinedAbstraction", "ConcreteImplementor"]),
    ("Interpreter",     ["Interpreter", "interpret", "Expression", "Context"]),
    ("Memento",         ["Memento", "Originator", "Caretaker", "getState", "restore"]),
]

def _detect_patterns(all_names: list[str]) -> list[str]:
    """Detect design patterns from a list of class/function names."""
    combined = " ".join(all_names)
    found = []
    for pattern_name, signals in _PATTERN_SIGNALS:
        if any(sig in combined for sig in signals):
            found.append(pattern_name)
    return found


# ─── Code Smell Detector ──────────────────────────────────────────────────────

def _detect_smells(data_by_file: dict[str, dict]) -> list[str]:
    smells = []
    for filepath, data in data_by_file.items():
        funcs = data.get("functions", [])
        classes = data.get("classes", [])
        imports = data.get("imports", [])

        if len(funcs) > 20:
            smells.append(f"God File (too many functions: {len(funcs)}) → {Path(filepath).name}")
        if len(classes) > 8:
            smells.append(f"Bloated module ({len(classes)} classes) → {Path(filepath).name}")
        if len(imports) > 12:
            smells.append(f"High coupling (too many imports: {len(imports)}) → {Path(filepath).name}")
        for cls in classes:
            if "Manager" in cls and "Service" not in cls:
                smells.append(f"Vague naming ('Manager' anti-pattern) → {cls}")
                break

    return list(dict.fromkeys(smells))[:10]  # deduplicate, cap at 10


# ─── Zip Processor ────────────────────────────────────────────────────────────

def _should_skip(path: str) -> bool:
    parts = set(path.replace("\\", "/").split("/"))
    return bool(parts & SKIP_DIRS) or any(p.startswith(".") for p in parts)


def process_zip(zip_path: Path) -> dict | None:
    if not zip_path.exists():
        print(f"  [SKIP] Not found: {zip_path.name}")
        return None

    print(f"\n  Processing: {zip_path.name} ({zip_path.stat().st_size // 1024} KB)")

    data_by_file: dict[str, dict] = {}
    all_classes: list[str] = []
    all_functions: list[str] = []
    lang_counter: dict[str, int] = {}

    with tempfile.TemporaryDirectory(prefix="demo_memory_") as td:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(td)
        except zipfile.BadZipFile:
            print(f"  [ERROR] Bad zip file: {zip_path.name}")
            return None

        file_count = 0
        for root, dirs, files in os.walk(td):
            dirs[:] = [d for d in dirs if not _should_skip(os.path.join(root, d).replace(td, ""))]
            if _should_skip(root.replace(td, "")):
                continue

            for fname in sorted(files):
                if file_count >= MAX_FILES_PER_ZIP:
                    break
                ext = Path(fname).suffix.lower()
                if ext not in SUPPORTED_EXTS:
                    continue

                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, td)
                parsed = _parse_file(fpath)
                if not parsed:
                    continue

                data_by_file[rel] = parsed
                all_classes.extend(parsed.get("classes", []))
                all_functions.extend(parsed.get("functions", []))
                lang_counter[parsed["lang"]] = lang_counter.get(parsed["lang"], 0) + 1
                file_count += 1

    if not data_by_file:
        print(f"  [WARN] No parseable files found in {zip_path.name}")
        return None

    all_names = all_classes + all_functions
    patterns = _detect_patterns(all_names)
    smells = _detect_smells(data_by_file)

    # Build an architecture summary text (like what the LLM would see)
    summary_lines = [f"=== CODEBASE: {zip_path.stem} ==="]
    for rel, data in list(data_by_file.items())[:20]:
        summary_lines.append(f"\n[FILE] {rel}")
        if data.get("classes"):
            summary_lines.append(f"  Classes: {', '.join(data['classes'][:10])}")
        if data.get("functions"):
            summary_lines.append(f"  Functions: {', '.join(data['functions'][:10])}")
        if data.get("imports"):
            summary_lines.append(f"  Imports: {', '.join(data['imports'][:8])}")
    ast_summary_text = "\n".join(summary_lines)

    top_classes = list(dict.fromkeys(all_classes))[:30]
    top_functions = list(dict.fromkeys(all_functions))[:30]

    entry = {
        "source": str(zip_path.name),
        "codebase_name": zip_path.stem,
        "indexed_at": datetime.now().isoformat(),
        "stats": {
            "files_parsed": len(data_by_file),
            "total_classes": len(all_classes),
            "total_functions": len(all_functions),
            "languages": lang_counter,
        },
        "design_patterns_detected": patterns,
        "code_smells_detected": smells,
        "top_components": {
            "classes": top_classes,
            "functions": top_functions[:30],
        },
        "architecture_summary": ast_summary_text,
        "architectural_insights": _generate_insights(zip_path.stem, patterns, lang_counter, len(all_classes), smells),
        "file_breakdown": [
            {
                "file": rel,
                "lang": data["lang"],
                "classes": data.get("classes", [])[:8],
                "functions": data.get("functions", [])[:8],
                "imports": data.get("imports", [])[:6],
            }
            for rel, data in data_by_file.items()
        ],
    }

    print(f"  ✅ Parsed {len(data_by_file)} files | Patterns: {patterns[:4]} | Languages: {list(lang_counter.keys())}")
    return entry


def _generate_insights(name: str, patterns: list[str], langs: dict, class_count: int, smells: list[str]) -> list[str]:
    """Generate human-readable architectural insights for the demo."""
    insights = []
    primary_lang = max(langs, key=langs.get) if langs else "unknown"

    insights.append(
        f"Codebase '{name}' is primarily written in {primary_lang.upper()} "
        f"with {class_count} classes across {sum(langs.values())} files."
    )

    if patterns:
        insights.append(
            f"Detected {len(patterns)} design pattern(s): {', '.join(patterns[:6])}. "
            "These patterns indicate a well-structured object-oriented architecture."
        )
        if "Singleton" in patterns:
            insights.append("Singleton pattern found — ensure thread safety in concurrent environments.")
        if "Factory" in patterns or "Abstract Factory" in patterns:
            insights.append("Factory pattern usage promotes loose coupling and supports Open/Closed principle.")
        if "Observer" in patterns:
            insights.append("Observer/Event pattern detected — good for decoupled event-driven systems.")
        if "Strategy" in patterns:
            insights.append("Strategy pattern enables runtime algorithm selection without modifying client code.")
        if "Decorator" in patterns:
            insights.append("Decorator pattern allows behavior extension without subclassing.")
        if "Command" in patterns:
            insights.append("Command pattern encapsulates requests as objects, enabling undo/redo and queuing.")
        if "Builder" in patterns:
            insights.append("Builder pattern used to construct complex objects step-by-step.")

    if smells:
        insights.append(
            f"Code quality concerns: {len(smells)} potential smell(s) detected. "
            "Review flagged files for refactoring opportunities."
        )
    else:
        insights.append("No major code smells detected — codebase appears well-modularized.")

    if len(langs) > 2:
        insights.append(
            f"Multi-language codebase ({', '.join(langs.keys())}) — "
            "ensure clear language boundaries and consistent interface contracts."
        )

    insights.append(
        "Recommended architecture layer for this knowledge: "
        "business/domain layer patterns. Reusable across similar OOP design challenges."
    )

    return insights


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Architect-AI — Demo Memory Builder")
    print("  (Standalone — NOT connected to agent pipeline)")
    print("=" * 60)

    entries = []
    for zip_path in ZIP_FILES:
        entry = process_zip(zip_path)
        if entry:
            entries.append(entry)

    if not entries:
        print("\n[ERROR] No entries generated. Make sure the zip files are present.")
        return

    memory_doc = {
        "meta": {
            "tool": "Architect-AI Demo Memory Builder",
            "version": "1.0.0",
            "description": (
                "This is a DEMO knowledge base — a human-readable representation of what the "
                "ChromaDB vector store would contain after training on real codebases. "
                "Each entry represents a parsed codebase with detected patterns, smells, and architectural insights."
            ),
            "generated_at": datetime.now().isoformat(),
            "total_codebases": len(entries),
            "note": "In production, these entries are chunked and stored as vector embeddings in ChromaDB "
                    "using Ollama nomic-embed-text. Retrieved at query time via semantic similarity search (k=3).",
        },
        "memory_entries": entries,
        "demo_retrieval_example": {
            "query": "How to implement the Observer pattern in Java?",
            "top_k": 3,
            "simulated_result": [
                {
                    "rank": 1,
                    "source": entries[0]["source"] if entries else "N/A",
                    "relevance_score": 0.91,
                    "excerpt": (
                        entries[0]["architecture_summary"][:400] + "..."
                        if entries else "N/A"
                    ),
                },
                {
                    "rank": 2,
                    "source": entries[1]["source"] if len(entries) > 1 else "N/A",
                    "relevance_score": 0.87,
                    "excerpt": (
                        entries[1]["architecture_summary"][:400] + "..."
                        if len(entries) > 1 else "N/A"
                    ),
                },
                {
                    "rank": 3,
                    "source": entries[2]["source"] if len(entries) > 2 else "N/A",
                    "relevance_score": 0.83,
                    "excerpt": (
                        entries[2]["architecture_summary"][:400] + "..."
                        if len(entries) > 2 else "N/A"
                    ),
                },
            ],
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_doc, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  ✅ Demo memory saved → {OUTPUT_FILE.name}")
    print(f"  📦 Codebases indexed: {len(entries)}")
    for e in entries:
        print(f"     • {e['codebase_name']}: {e['stats']['files_parsed']} files, "
              f"{len(e['design_patterns_detected'])} patterns detected")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
