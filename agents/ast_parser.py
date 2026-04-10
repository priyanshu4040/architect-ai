"""
AST Parser Utility
Extracts classes, functions, and imports from Python files to build a structural graph.
"""

import ast
import os
import json
from typing import Dict, List

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
            # Extract base classes (inheritance)
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
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Only count top-level or class-level functions if we want to be simple,
            # but ast.walk gets all. We'll just collect names.
            functions.append(node.name)

    return {
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "raw_classes": [  # structured class info for graph use
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

def generate_ast_summary(path: str) -> str:
    """
    Crawls a directory (or single file), parses Python files,
    and returns a formatted structural summary of the codebase.
    """
    if not os.path.exists(path):
        return "Path does not exist."

    summary_lines = ["=== CODEBASE ARCHITECTURE & DEPENDENCY GRAPH ==="]

    if os.path.isfile(path):
        if path.endswith(".py"):
            summary_lines.append(f"\n[FILE] {os.path.basename(path)}")
            data = parse_python_file(path)
            _format_file_data(data, summary_lines)
        else:
            summary_lines.append("AST Parsing skipped (not a Python file).")

    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            if any(part.startswith('.') for part in root.split(os.sep)) or "venv" in root or "__pycache__" in root:
                continue

            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    relpath = os.path.relpath(filepath, path)
                    
                    data = parse_python_file(filepath)
                    if "error" in data:
                        continue
                        
                    summary_lines.append(f"\n[FILE] {relpath}")
                    _format_file_data(data, summary_lines)

    if len(summary_lines) == 1:
        summary_lines.append("\nNo Python AST structure extracted.")

    return "\n".join(summary_lines)

def _format_file_data(data: Dict, summary_lines: List[str]):
    """Helper to format parsed data into text lines."""
    if data.get("imports"):
        summary_lines.append(f"  Imports: {', '.join(data['imports'][:10])}{'...' if len(data['imports']) > 10 else ''}")
    if data.get("classes"):
        summary_lines.append(f"  Classes: {', '.join(data['classes'])}")
    if data.get("functions"):
        summary_lines.append(f"  Functions: {', '.join(data['functions'][:15])}{'...' if len(data['functions']) > 15 else ''}")
