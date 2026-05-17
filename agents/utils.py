"""
Utility functions for the system.
"""

import os

# Concise shared rules (kept short to save prompt tokens).
PROMPT_GROUNDING = (
    "Be specific to the input. Justify choices for THIS project. "
    "No generic 'use React and Node' without domain reasoning. "
    "Brownfield: only list detected items with file-path evidence; suggestions go in suggested_modules."
)


def read_codebase(path: str) -> str:
    """Reads code files — avoid using full dump for brownfield LLM (use compact parser summary)."""
    if not os.path.exists(path):
        return ""

    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f"--- FILE: {os.path.basename(path)} ---\n" + f.read() + "\n\n"
        except Exception as e:
            return f"Error reading file {path}: {e}"

    allowed_exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".cs", ".rb", ".php"}
    code_content = []

    for root, _, files in os.walk(path):
        if any(part.startswith(".") for part in root.split(os.sep)) or "node_modules" in root or "venv" in root or "__pycache__" in root:
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in allowed_exts:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        rel_path = os.path.relpath(file_path, path)
                        code_content.append(f"--- FILE: {rel_path} ---\n{f.read()}\n")
                except Exception:
                    pass

    return "\n".join(code_content)
