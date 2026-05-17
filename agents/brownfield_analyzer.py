"""
Deterministic deep analysis for brownfield ZIP/path uploads.
Builds a compact, evidence-backed summary for the LLM (no full file contents).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Token-saving: skip vendor/build dirs; cap items sent to LLM.
_SKIP_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__", ".git",
    "dist", "build", ".next", "coverage", ".cache", "vendor", "target",
}

_CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".cs", ".rb", ".php"}
_MAX_FILE_BYTES = 50_000
_MAX_READ_LINES = 150
_MAX_TREE_PATHS = 30
_MAX_MODULES = 20
_MAX_APIS = 20
_MAX_ISSUES = 15
_MAX_SECURITY_SIGNALS = 10
_MAX_DEPS_PER_MANIFEST = 10

_ROUTE_PATTERNS = [
    (re.compile(r"@(?:app|router)\.(get|post|put|patch|delete|options)\s*\(\s*['\"]([^'\"]+)['\"]", re.I), "fastapi"),
    (re.compile(r"@(?:Get|Post|Put|Patch|Delete)Mapping\s*\(\s*(?:value\s*=\s*)?['\"]([^'\"]+)['\"]", re.I), "spring"),
    (re.compile(r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.I), "express"),
    (re.compile(r"app\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.I), "express"),
    (re.compile(r"path\s*\(\s*['\"]([^'\"]+)['\"]", re.I), "django"),
    (re.compile(r"<Route\s+[^>]*path\s*=\s*['\"]([^'\"]+)['\"]", re.I), "react-router"),
]

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
]

_MODULE_TYPE_HINTS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"controller", re.I), "controller"),
    (re.compile(r"service", re.I), "service"),
    (re.compile(r"(model|entity|schema)", re.I), "model"),
    (re.compile(r"route", re.I), "route"),
    (re.compile(r"component", re.I), "component"),
    (re.compile(r"page", re.I), "page"),
    (re.compile(r"middleware", re.I), "config"),
    (re.compile(r"(util|helper)", re.I), "utility"),
]


def _should_skip(path: str) -> bool:
    parts = set(path.replace("\\", "/").split("/"))
    return bool(parts & _SKIP_DIRS) or any(p.startswith(".") for p in parts)


def _read_text(path: str, limit_bytes: int = _MAX_FILE_BYTES) -> str:
    try:
        size = os.path.getsize(path)
        if size > limit_bytes:
            return ""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= _MAX_READ_LINES:
                    break
                lines.append(line)
            return "".join(lines)
    except Exception:
        return ""


def _infer_module_type(rel_path: str, name: str) -> str:
    path_low = rel_path.lower()
    if "/pages/" in path_low or path_low.startswith("pages/"):
        return "page"
    if "/components/" in path_low or path_low.startswith("components/"):
        return "component"
    for pat, kind in _MODULE_TYPE_HINTS:
        if pat.search(name) or pat.search(path_low):
            return kind
    return "unknown"


def _module_name_from_file(rel_path: str) -> str:
    base = os.path.splitext(os.path.basename(rel_path))[0]
    if base in ("index", "__init__"):
        parent = os.path.basename(os.path.dirname(rel_path))
        return parent or base
    return base


def _file_tree_summary(root: str, max_depth: int = 4) -> List[str]:
    paths: List[str] = []

    def walk(dirpath: str, depth: int) -> None:
        if depth > max_depth or len(paths) >= _MAX_TREE_PATHS:
            return
        try:
            entries = sorted(os.listdir(dirpath))
        except OSError:
            return
        for name in entries:
            if name.startswith(".") or name in _SKIP_DIRS:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            if os.path.isdir(full):
                paths.append(rel + "/")
                walk(full, depth + 1)
            else:
                paths.append(rel)
            if len(paths) >= _MAX_TREE_PATHS:
                return

    walk(root, 0)
    return paths


def _dependency_summary(root: str) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {"npm": [], "pip": [], "maven": [], "gradle": [], "go": []}

    pkg_path = os.path.join(root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            pkg = json.loads(_read_text(pkg_path, 100_000) or "{}")
            deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
            out["npm"] = list(deps.keys())[:_MAX_DEPS_PER_MANIFEST]
        except Exception:
            pass

    req_path = os.path.join(root, "requirements.txt")
    if os.path.isfile(req_path):
        out["pip"] = [
            ln.split("==")[0].split(">=")[0].strip()
            for ln in (_read_text(req_path) or "").splitlines()
            if ln.strip() and not ln.startswith("#")
        ][: _MAX_DEPS_PER_MANIFEST]

    pyproject = os.path.join(root, "pyproject.toml")
    if os.path.isfile(pyproject):
        text = _read_text(pyproject) or ""
        out["pip"].extend(
            m.group(1) for m in re.finditer(r'["\']([a-zA-Z0-9_-]+)["\']\s*=', text)
        )
        out["pip"] = list(dict.fromkeys(out["pip"]))[:_MAX_DEPS_PER_MANIFEST]

    if os.path.isfile(os.path.join(root, "pom.xml")):
        text = _read_text(os.path.join(root, "pom.xml")) or ""
        out["maven"] = re.findall(r"<artifactId>([^<]+)</artifactId>", text)[:_MAX_DEPS_PER_MANIFEST]

    if os.path.isfile(os.path.join(root, "build.gradle")):
        text = _read_text(os.path.join(root, "build.gradle")) or ""
        out["gradle"] = re.findall(r"['\"]([a-zA-Z0-9_.:-]+)['\"]", text)[:_MAX_DEPS_PER_MANIFEST]

    if os.path.isfile(os.path.join(root, "go.mod")):
        text = _read_text(os.path.join(root, "go.mod")) or ""
        out["go"] = [ln.split()[0] for ln in text.splitlines() if ln.strip().startswith("require")][:5]

    return out


def _detect_stack_from_manifests(root: str, deps: Dict[str, List[str]]) -> Dict[str, Any]:
    """Stack with evidence file paths (parser-only, no guessing)."""
    stack: Dict[str, Any] = {
        "frontend": {"value": "", "evidence": []},
        "backend": {"value": "", "evidence": []},
        "database": {"value": "", "evidence": []},
        "authentication": {"value": "", "evidence": []},
        "deployment": [],
        "api_style": {"value": "", "evidence": []},
    }

    def set_field(key: str, value: str, evidence: str) -> None:
        if not value:
            return
        field = stack.get(key)
        if isinstance(field, dict):
            if not field.get("value"):
                field["value"] = value
            if evidence and evidence not in field.get("evidence", []):
                field.setdefault("evidence", []).append(evidence)

    pkg_path = os.path.join(root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            pkg = json.loads(_read_text(pkg_path, 100_000) or "{}")
            dep_keys = " ".join({**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}).lower()
            ev = "package.json"
            if "next" in dep_keys:
                set_field("frontend", "Next.js", ev)
            elif "react" in dep_keys:
                set_field("frontend", "React", ev)
            elif "vue" in dep_keys:
                set_field("frontend", "Vue", ev)
            elif "angular" in dep_keys or "@angular/core" in dep_keys:
                set_field("frontend", "Angular", ev)
            if "express" in dep_keys:
                set_field("backend", "Express (Node.js)", ev)
            elif "fastify" in dep_keys:
                set_field("backend", "Fastify (Node.js)", ev)
            if "mongoose" in dep_keys:
                set_field("database", "MongoDB (Mongoose)", ev)
            elif "prisma" in dep_keys:
                set_field("database", "SQL via Prisma", ev)
            if any(x in dep_keys for x in ("passport", "jsonwebtoken", "next-auth")):
                set_field("authentication", "JWT/Session (npm auth libs)", ev)
            if "graphql" in dep_keys:
                set_field("api_style", "GraphQL", ev)
            elif stack["backend"].get("value"):
                set_field("api_style", "REST", ev)
        except Exception:
            pass

    req_path = os.path.join(root, "requirements.txt")
    if os.path.isfile(req_path):
        req = (_read_text(req_path) or "").lower()
        ev = "requirements.txt"
        if "fastapi" in req:
            set_field("backend", "FastAPI", ev)
        elif "django" in req:
            set_field("backend", "Django", ev)
        elif "flask" in req:
            set_field("backend", "Flask", ev)
        if "sqlalchemy" in req or "psycopg" in req:
            set_field("database", "PostgreSQL/SQLAlchemy", ev)
        elif "pymongo" in req:
            set_field("database", "MongoDB", ev)
        if "python-jose" in req or "pyjwt" in req:
            set_field("authentication", "JWT (Python)", ev)

    if os.path.isfile(os.path.join(root, "pom.xml")):
        set_field("backend", "Spring Boot (Java)", "pom.xml")
    if os.path.isfile(os.path.join(root, "build.gradle")):
        set_field("backend", "Gradle (Java/Kotlin)", "build.gradle")
    if os.path.isfile(os.path.join(root, "go.mod")):
        set_field("backend", "Go", "go.mod")
    if os.path.isfile(os.path.join(root, "docker-compose.yml")) or os.path.isfile(os.path.join(root, "Dockerfile")):
        stack["deployment"].append("Docker")
    if os.path.isfile(os.path.join(root, "vercel.json")):
        stack["deployment"].append("Vercel")
    if os.path.isfile(os.path.join(root, "netlify.toml")):
        stack["deployment"].append("Netlify")

    return stack


def _stack_to_flat(stack: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten evidence stack for legacy merge/UI fields."""
    flat: Dict[str, Any] = {
        "frontend": "",
        "backend": "",
        "database": "",
        "authentication": "",
        "deployment": stack.get("deployment") or [],
        "api_style": "",
    }
    for key in ("frontend", "backend", "database", "authentication", "api_style"):
        val = stack.get(key)
        if isinstance(val, dict):
            flat[key] = val.get("value") or ""
        elif isinstance(val, str):
            flat[key] = val
    return flat


def _detect_modules_from_files(root: str) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    modules: List[Dict[str, str]] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _should_skip(os.path.join(dirpath, d))]
        if _should_skip(dirpath):
            continue
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in _CODE_EXTS:
                continue
            fp = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(fp) > _MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            rel = os.path.relpath(fp, root).replace("\\", "/")
            name = _module_name_from_file(rel)
            key = f"{name}:{rel}"
            if key in seen:
                continue
            seen.add(key)
            mod_type = _infer_module_type(rel, name)
            if mod_type == "unknown" and ext in (".tsx", ".jsx"):
                mod_type = "component"
            modules.append({
                "name": name,
                "type": mod_type,
                "path": rel,
                "evidence": rel,
                "confidence": "high",
            })
            if len(modules) >= _MAX_MODULES:
                return modules
    return modules


def _extract_routes(root: str, max_files: int = 50) -> List[Dict[str, str]]:
    routes: List[Dict[str, str]] = []
    count = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _should_skip(os.path.join(dirpath, d))]
        if _should_skip(dirpath):
            continue
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in _CODE_EXTS:
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root).replace("\\", "/")
            text = _read_text(fp)
            if not text:
                continue
            for pat, framework in _ROUTE_PATTERNS:
                for m in pat.finditer(text):
                    groups = m.groups()
                    if len(groups) == 2:
                        method, path = groups[0].upper(), groups[1]
                    else:
                        method, path = "GET", groups[0]
                    routes.append({
                        "method": method,
                        "path": path,
                        "file": rel,
                        "evidence": rel,
                        "purpose": f"{framework} pattern",
                    })
            count += 1
            if count >= max_files or len(routes) >= _MAX_APIS:
                return routes[:_MAX_APIS]
    return routes[:_MAX_APIS]


def _security_signals(root: str, max_files: int = 60) -> List[Dict[str, str]]:
    signals: List[Dict[str, str]] = []
    if os.path.isfile(os.path.join(root, ".env")):
        signals.append({
            "signal": ".env file present",
            "evidence": ".env",
            "severity": "medium",
        })
    gitignore = os.path.join(root, ".gitignore")
    gi_text = _read_text(gitignore, 10_000) if os.path.isfile(gitignore) else ""
    if os.path.isfile(os.path.join(root, ".env")) and ".env" not in gi_text:
        signals.append({
            "signal": ".env may not be gitignored",
            "evidence": ".gitignore",
            "severity": "high",
        })

    scanned = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _should_skip(os.path.join(dirpath, d))]
        for fn in files:
            if scanned >= max_files or len(signals) >= _MAX_SECURITY_SIGNALS:
                break
            ext = os.path.splitext(fn)[1].lower()
            if ext not in _CODE_EXTS and fn not in (".env", "config.py", "settings.py"):
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root).replace("\\", "/")
            text = _read_text(fp)
            scanned += 1
            if not text:
                continue
            for pat in _SECRET_PATTERNS:
                if pat.search(text):
                    signals.append({
                        "signal": "Possible hardcoded secret",
                        "evidence": rel,
                        "severity": "high",
                    })
                    break
            if re.search(r"cors.*\*|Access-Control-Allow-Origin.*\*", text, re.I):
                signals.append({
                    "signal": "Permissive CORS wildcard",
                    "evidence": rel,
                    "severity": "medium",
                })
    return signals[:_MAX_SECURITY_SIGNALS]


def _folder_analysis(root: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not os.path.isdir(root):
        return rows
    for name in sorted(os.listdir(root))[:20]:
        full = os.path.join(root, name)
        if not os.path.isdir(full) or name.startswith(".") or name in _SKIP_DIRS:
            continue
        rows.append({
            "folder": name,
            "purpose": "Top-level project folder",
            "quality": "OK",
            "suggestion": "",
        })
    return rows


def _layer_analysis(root: str) -> List[Dict[str, str]]:
    found: Set[str] = set()
    layer_map = {
        "controllers": "presentation", "routes": "presentation", "handlers": "presentation",
        "api": "presentation", "pages": "presentation", "views": "presentation",
        "services": "business", "service": "business", "domain": "business",
        "repositories": "data", "models": "data", "entities": "data",
    }
    for dirpath, dirs, _ in os.walk(root):
        if _should_skip(dirpath):
            continue
        for d in dirs:
            if d.lower() in layer_map:
                found.add(layer_map[d.lower()])
    issues: List[Dict[str, str]] = []
    if "presentation" in found and "business" not in found:
        issues.append({
            "issue": "Missing service/business layer folder",
            "severity": "Medium",
            "reason": "Presentation folders found without services/",
            "suggested_fix": "Extract business logic into service modules",
            "affected_area": "backend",
            "evidence": "folder scan",
        })
    return issues[:_MAX_ISSUES]


def _maintainability_scan(root: str) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if not any(os.path.isfile(os.path.join(root, n)) for n in ("README.md", "readme.md")):
        issues.append({
            "issue": "Missing README",
            "severity": "Low",
            "reason": "No README at project root",
            "suggested_fix": "Add setup and architecture overview",
            "affected_area": "docs",
            "evidence": "root",
        })
    return issues[:5]


def _security_issues_from_signals(signals: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        {
            "issue": s.get("signal", ""),
            "severity": (s.get("severity") or "medium").capitalize(),
            "reason": f"Detected in {s.get('evidence', '')}",
            "suggested_fix": "Review and remediate per security baseline",
            "affected_area": s.get("evidence", ""),
        }
        for s in signals
    ]


def _build_compact_summary(
    *,
    file_tree: List[str],
    dependencies: Dict[str, List[str]],
    stack: Dict[str, Any],
    modules: List[Dict[str, str]],
    apis: List[Dict[str, str]],
    security_signals: List[Dict[str, str]],
    arch_signals: List[Dict[str, str]],
    skipped: List[str],
) -> Dict[str, Any]:
    return {
        "file_tree_summary": file_tree,
        "dependency_summary": dependencies,
        "detected_stack": stack,
        "detected_modules": modules,
        "detected_apis": apis,
        "security_signals": security_signals,
        "architecture_signals": arch_signals,
        "large_files_skipped": skipped,
        "ignored_folders": sorted(_SKIP_DIRS),
    }


def _format_compact_for_llm(compact: Dict[str, Any]) -> str:
    # Token-saving: single JSON blob, capped length.
    text = json.dumps(compact, separators=(",", ":"))
    return text[:8000]


def run_deep_brownfield_analysis(path: str) -> Dict[str, Any]:
    """
    Main entry: parser-authoritative dict for service + LLM.
    """
    if not os.path.exists(path):
        return {"error": "Path does not exist", "_parser_stats": {"error": True}}

    root = path if os.path.isdir(path) else os.path.dirname(path)
    files_scanned = 0
    files_skipped = 0
    large_skipped: List[str] = []

    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _should_skip(os.path.join(dirpath, d))]
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in _CODE_EXTS:
                continue
            fp = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(fp)
                if size > _MAX_FILE_BYTES:
                    files_skipped += 1
                    large_skipped.append(os.path.relpath(fp, root).replace("\\", "/"))
                    continue
                files_scanned += 1
            except OSError:
                files_skipped += 1

    file_tree = _file_tree_summary(root)
    dependencies = _dependency_summary(root)
    stack_evidence = _detect_stack_from_manifests(root, dependencies)
    stack_flat = _stack_to_flat(stack_evidence)
    modules = _detect_modules_from_files(root)
    routes = _extract_routes(root)
    security_signals = _security_signals(root)
    arch_issues = _layer_analysis(root)
    maintainability = _maintainability_scan(root)
    security_issues = _security_issues_from_signals(security_signals)

    compact = _build_compact_summary(
        file_tree=file_tree,
        dependencies=dependencies,
        stack=stack_evidence,
        modules=modules,
        apis=routes,
        security_signals=security_signals,
        arch_signals=arch_issues,
        skipped=large_skipped[:10],
    )
    compact_text = _format_compact_for_llm(compact)

    parser_stats = {
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "modules_detected": len(modules),
        "apis_detected": len(routes),
        "summary_chars": len(compact_text),
    }

    evolution = {
        "immediate_fixes": [
            i["suggested_fix"] for i in security_issues if i.get("severity", "").lower() == "high"
        ][:5],
        "short_term_improvements": [i["suggested_fix"] for i in arch_issues if i.get("suggested_fix")][:5],
        "long_term_improvements": [],
    }

    flat_module_names = [m["name"] for m in modules]

    return {
        "project_summary": (
            f"Detected {len(modules)} modules, {len(routes)} API routes from uploaded codebase."
        ),
        "detected_stack": stack_flat,
        "detected_stack_evidence": stack_evidence,
        "folder_analysis": _folder_analysis(root),
        "detected_modules": modules,
        "detected_modules_flat": flat_module_names,
        "detected_apis": routes,
        "suggested_modules": [],
        "architecture_issues": arch_issues,
        "security_issues": security_issues,
        "scalability_issues": [],
        "maintainability_issues": maintainability,
        "improvement_suggestions": [],
        "evolution_plan": evolution,
        "final_summary": "",
        "compact_summary": compact,
        "_analysis_text": compact_text,
        "_parser_stats": parser_stats,
        "is_fallback": False,
    }
