"""
AST Parser Utility
Extracts classes, functions, and imports from Python, JavaScript, TypeScript,
TSX, JSX, Java, Go, C#, Ruby, and PHP files to build a structural graph.

Python files use the native `ast` module for precision.
All other languages use regex-based extraction.
"""

import ast
import os
import re
import json
from typing import Dict, List

# ─────────────────────────────────────────────
# Python AST parser (high-precision)
# ─────────────────────────────────────────────

def parse_python_file(filepath: str) -> Dict:
    """Parses a single Python file and returns its structural elements."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except Exception as e:
        return {"error": str(e)}

    imports = []
    classes = []
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    imports.append(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            if bases:
                classes.append(f"{node.name} (Inherits: {', '.join(bases)})")
            else:
                classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    return {
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "raw_classes": [
            {
                "name": node.name,
                "bases": [
                    (base.id if isinstance(base, ast.Name) else base.attr)
                    for base in node.bases
                    if isinstance(base, (ast.Name, ast.Attribute))
                ]
            }
            for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
    }


# ─────────────────────────────────────────────
# Generic regex-based parser (JS/TS/TSX/JSX/Java/Go/C#/etc.)
# ─────────────────────────────────────────────

def parse_generic_file(filepath: str, lang: str) -> Dict:
    """
    Regex-based extractor for non-Python source files.
    Extracts classes, exported functions/components, and imports.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except Exception as e:
        return {"error": str(e)}

    imports: List[str] = []
    classes: List[str] = []
    functions: List[str] = []

    if lang in ("js", "ts", "jsx", "tsx"):
        # imports: import X from 'Y'  |  import { A, B } from 'C'  | require('D')
        for m in re.finditer(r"""import\s+(?:.*?from\s+)?['"]([^'"]+)['"]""", source):
            imports.append(m.group(1))
        for m in re.finditer(r"""require\(['"]([^'"]+)['"]\)""", source):
            imports.append(m.group(1))
        # import * as NS from 'mod'
        for m in re.finditer(r"""import\s+\*\s+as\s+\w+\s+from\s+['"]([^'"]+)['"]""", source):
            imports.append(m.group(1))
        # dynamic import('x')
        for m in re.finditer(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""", source):
            imports.append(m.group(1))

        # classes: class MyComp extends X
        for m in re.finditer(r"\bclass\s+(\w+)(?:\s+extends\s+(\w+))?", source):
            name = m.group(1)
            base = m.group(2)
            classes.append(f"{name} (extends: {base})" if base else name)

        # interfaces (TS)
        for m in re.finditer(r"\binterface\s+(\w+)", source):
            classes.append(f"{m.group(1)} [interface]")

        # type aliases (TS)
        for m in re.finditer(r"\btype\s+(\w+)\s*=", source):
            classes.append(f"{m.group(1)} [type]")

        # exported functions and arrow components
        for m in re.finditer(
            r"export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)", source
        ):
            functions.append(m.group(1))
        for m in re.finditer(r"export\s+default\s+class\s+(\w+)", source):
            classes.append(m.group(1))
        # Top-level function declarations (common in TS/React)
        for m in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            source,
        ):
            functions.append(m.group(1))
        # const MyComponent = () =>  /  const myFn = async () =>
        for m in re.finditer(
            r"(?:export\s+)?const\s+(\w+)\s*[:=].*?(?:=>|\bfunction\b)", source
        ):
            functions.append(m.group(1))

    elif lang == "java":
        for m in re.finditer(r"^import\s+([\w.]+);", source, re.MULTILINE):
            imports.append(m.group(1))
        for m in re.finditer(
            r"\b(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)"
            r"(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?", source
        ):
            name = m.group(1)
            base = m.group(2)
            classes.append(f"{name} (extends: {base})" if base else name)
        for m in re.finditer(r"\binterface\s+(\w+)", source):
            classes.append(f"{m.group(1)} [interface]")
        for m in re.finditer(
            r"\b(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(", source
        ):
            functions.append(m.group(1))

    elif lang == "go":
        for m in re.finditer(r'"([\w./]+)"', source):
            imports.append(m.group(1))
        for m in re.finditer(r"\btype\s+(\w+)\s+struct\b", source):
            classes.append(f"{m.group(1)} [struct]")
        for m in re.finditer(r"\btype\s+(\w+)\s+interface\b", source):
            classes.append(f"{m.group(1)} [interface]")
        for m in re.finditer(r"\bfunc\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", source):
            functions.append(m.group(1))

    elif lang in ("cs", "csharp"):
        for m in re.finditer(r"^using\s+([\w.]+);", source, re.MULTILINE):
            imports.append(m.group(1))
        for m in re.finditer(
            r"\b(?:public|private|internal|protected)?\s*(?:abstract\s+|sealed\s+)?class\s+(\w+)", source
        ):
            classes.append(m.group(1))
        for m in re.finditer(r"\binterface\s+(\w+)", source):
            classes.append(f"{m.group(1)} [interface]")
        for m in re.finditer(
            r"\b(?:public|private|protected|internal)\s+(?:static\s+|async\s+|override\s+)?[\w<>\[\]]+\s+(\w+)\s*\(", source
        ):
            functions.append(m.group(1))

    elif lang == "rb":
        for m in re.finditer(r"^require(?:_relative)?\s+['\"]([^'\"]+)['\"]", source, re.MULTILINE):
            imports.append(m.group(1))
        for m in re.finditer(r"\bclass\s+(\w+)(?:\s*<\s*(\w+))?", source):
            name, base = m.group(1), m.group(2)
            classes.append(f"{name} < {base}" if base else name)
        for m in re.finditer(r"\bdef\s+(\w+)", source):
            functions.append(m.group(1))

    elif lang == "php":
        for m in re.finditer(r"(?:require|include)(?:_once)?\s*['\"]([^'\"]+)['\"]", source):
            imports.append(m.group(1))
        for m in re.finditer(r"\bclass\s+(\w+)(?:\s+extends\s+(\w+))?", source):
            name, base = m.group(1), m.group(2)
            classes.append(f"{name} extends {base}" if base else name)
        for m in re.finditer(r"\bfunction\s+(\w+)\s*\(", source):
            functions.append(m.group(1))

    # Deduplicate & cap
    return {
        "imports": list(dict.fromkeys(imports))[:20],
        "classes": list(dict.fromkeys(classes))[:30],
        "functions": list(dict.fromkeys(functions))[:30],
        "raw_classes": []
    }


# ─────────────────────────────────────────────
# Extension → language mapping
# ─────────────────────────────────────────────

_EXT_TO_LANG = {
    ".py":   "python",
    ".js":   "js",
    ".jsx":  "jsx",
    ".ts":   "ts",
    ".tsx":  "tsx",
    ".java": "java",
    ".go":   "go",
    ".cs":   "csharp",
    ".rb":   "rb",
    ".php":  "php",
}

SUPPORTED_EXTENSIONS = set(_EXT_TO_LANG.keys())

# Directories to always skip
_SKIP_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__", ".git",
    "dist", "build", ".next", "coverage", ".cache", "vendor",
    "target",  # Java/Maven
}


def _should_skip_dir(dirpath: str) -> bool:
    parts = set(dirpath.replace("\\", "/").split("/"))
    return bool(parts & _SKIP_DIRS) or any(p.startswith(".") for p in parts)


def _parse_file(filepath: str) -> Dict | None:
    ext = os.path.splitext(filepath)[1].lower()
    lang = _EXT_TO_LANG.get(ext)
    if not lang:
        return None
    if lang == "python":
        data = parse_python_file(filepath)
    else:
        data = parse_generic_file(filepath, lang)
    if "error" in data:
        return None
    # Only return if we extracted something meaningful
    if not data.get("classes") and not data.get("functions") and not data.get("imports"):
        return None
    return data


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def generate_ast_summary(path: str) -> str:
    """
    Crawls a directory (or single file), parses all supported source files,
    and returns a formatted structural summary of the codebase for LLM context.

    Supported: Python, JavaScript, TypeScript, TSX, JSX, Java, Go, C#, Ruby, PHP.
    """
    if not os.path.exists(path):
        return "Path does not exist."

    summary_lines = ["=== CODEBASE ARCHITECTURE & DEPENDENCY GRAPH ==="]

    if os.path.isfile(path):
        data = _parse_file(path)
        if data:
            summary_lines.append(f"\n[FILE] {os.path.basename(path)}")
            _format_file_data(data, summary_lines)
        else:
            summary_lines.append("AST Parsing skipped (unsupported file type or no content found).")

    elif os.path.isdir(path):
        file_count = 0
        for root, dirs, files in os.walk(path):
            # Prune skipped directories in-place so os.walk won't recurse into them
            dirs[:] = [d for d in dirs if not _should_skip_dir(os.path.join(root, d))]

            if _should_skip_dir(root):
                continue

            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, path)
                data = _parse_file(filepath)
                if not data:
                    continue

                summary_lines.append(f"\n[FILE] {relpath}")
                _format_file_data(data, summary_lines)
                file_count += 1

                # Cap at 80 files to avoid overwhelming the LLM context window
                if file_count >= 80:
                    summary_lines.append("\n[TRUNCATED] Max file limit reached (80 files).")
                    break
            else:
                continue
            break

    if len(summary_lines) == 1:
        summary_lines.append(
            "\nNo supported source files found. "
            "Ensure the codebase contains .py, .ts, .tsx, .js, .jsx, .java, .go, .cs, .rb, or .php files."
        )

    return "\n".join(summary_lines)


def _format_file_data(data: Dict, summary_lines: List[str]):
    """Helper to format parsed data into text lines."""
    if data.get("imports"):
        summary_lines.append(
            f"  Imports: {', '.join(data['imports'][:12])}"
            f"{'...' if len(data['imports']) > 12 else ''}"
        )
    if data.get("classes"):
        summary_lines.append(
            f"  Classes/Interfaces: {', '.join(data['classes'][:20])}"
            f"{'...' if len(data['classes']) > 20 else ''}"
        )
    if data.get("functions"):
        summary_lines.append(
            f"  Functions/Components: {', '.join(data['functions'][:20])}"
            f"{'...' if len(data['functions']) > 20 else ''}"
        )



