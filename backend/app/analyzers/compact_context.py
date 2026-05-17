"""
Build token-bounded brownfield context for LLM agents (no full file dumps).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

# ~4 chars/token heuristic; stay under ~12k token budget for brownfield input slice.
MAX_CONTEXT_CHARS = 9000
MAX_SNIPPET_LINES = 150
MAX_SNIPPET_FILES = 5
MAX_KEY_FILES = 40

KEY_FILE_NAMES = frozenset({
    "package.json", "pom.xml", "build.gradle", "requirements.txt", "pyproject.toml",
    "Dockerfile", "docker-compose.yml", "main.py", "app.py", "manage.py",
    "vite.config.ts", "vite.config.js", "next.config.ts", "next.config.js",
    "tsconfig.json", "prisma/schema.prisma",
})

SKIP_DIRS = frozenset({
    "node_modules", ".git", "dist", "build", "target", "__pycache__",
    ".venv", "venv", "vendor", "coverage", ".next", "out",
})


def _read_head(path: str, max_lines: int = 30) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return "".join(line for i, line in enumerate(f) if i < max_lines)
    except OSError:
        return ""


def _collect_key_files(root: str) -> List[str]:
    found: List[str] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if any(p in SKIP_DIRS for p in rel_dir.split("/")):
            continue
        for fn in files:
            rel = f"{rel_dir}/{fn}" if rel_dir != "." else fn
            if fn in KEY_FILE_NAMES or rel.endswith("prisma/schema.prisma"):
                found.append(rel)
            if len(found) >= MAX_KEY_FILES:
                return found
    return found


def _build_snippets(root: str, key_files: List[str], line_budget: int) -> Dict[str, str]:
    snippets: Dict[str, str] = {}
    lines_used = 0
    for rel in key_files[:MAX_SNIPPET_FILES]:
        if lines_used >= line_budget:
            break
        fp = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(fp):
            continue
        text = _read_head(fp, max_lines=min(30, line_budget - lines_used))
        if not text.strip():
            continue
        line_count = text.count("\n") + 1
        lines_used += line_count
        snippets[rel] = text[:2000]
    return snippets


def build_brownfield_llm_context(
    project_root: str,
    detected_tech_stack: Dict[str, Any],
    deep_analysis: Dict[str, Any] | None = None,
) -> str:
    """
    Merge tech stack (source of truth) + parser summary into one compact JSON string.
    Truncates to MAX_CONTEXT_CHARS.
    """
    deep = deep_analysis or {}
    compact = deep.get("compact_summary") or {}
    if not compact and deep:
        compact = {
            "detected_modules": deep.get("detected_modules", [])[:20],
            "detected_apis": deep.get("detected_apis", [])[:20],
            "file_tree_summary": (deep.get("folder_analysis") or [])[:20],
        }

    key_files = _collect_key_files(project_root)
    snippets = _build_snippets(project_root, key_files, MAX_SNIPPET_LINES)

    payload: Dict[str, Any] = {
        "detected_tech_stack": {
            "languages": detected_tech_stack.get("languages", []),
            "language_percentages": detected_tech_stack.get("language_percentages", {}),
            "frameworks": detected_tech_stack.get("frameworks", []),
            "libraries": detected_tech_stack.get("libraries", []),
            "databases": detected_tech_stack.get("databases", []),
            "build_tools": detected_tech_stack.get("build_tools", []),
            "deployment": detected_tech_stack.get("deployment", []),
            "package_managers": detected_tech_stack.get("package_managers", []),
            "evidence": detected_tech_stack.get("evidence", {}),
            "confidence": detected_tech_stack.get("confidence", {}),
            "folder_structure": detected_tech_stack.get("folder_structure", []),
        },
        "dependency_graph_summary": compact.get("dependency_summary", {}),
        "folder_structure": detected_tech_stack.get("folder_structure") or compact.get("file_tree_summary", []),
        "key_files": key_files,
        "detected_modules": compact.get("detected_modules", [])[:20],
        "detected_apis": compact.get("detected_apis", [])[:20],
        "file_snippets": snippets,
        "rules": (
            "Use ONLY technologies/modules/files listed here. "
            "If not listed, say 'Not detected in uploaded codebase'."
        ),
    }

    text = json.dumps(payload, separators=(",", ":"))
    if len(text) > MAX_CONTEXT_CHARS:
        payload.pop("file_snippets", None)
        text = json.dumps(payload, separators=(",", ":"))
    if len(text) > MAX_CONTEXT_CHARS:
        text = text[:MAX_CONTEXT_CHARS] + '..."truncated":true}'
    return text
