"""
Deterministic tech-stack scanner (Linguist-style file evidence).
Scans extracted ZIP paths — no LLM guessing.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

SKIP_DIRS = frozenset({
    "node_modules", ".git", "dist", "build", "target", "__pycache__",
    ".venv", "venv", "vendor", "coverage", ".next", "out", ".cache",
})

SKIP_FILES = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
    "poetry.lock", "Cargo.lock",
})

BINARY_OR_MEDIA_EXTS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
    ".zip", ".tar", ".gz", ".woff", ".woff2", ".ttf", ".eot", ".mp4",
    ".mp3", ".wav", ".bin", ".exe", ".dll", ".so", ".dylib", ".class",
})

# extension -> language label(s)
EXT_LANGUAGES: Dict[str, List[str]] = {
    ".java": ["Java"],
    ".py": ["Python"],
    ".js": ["JavaScript"],
    ".jsx": ["JavaScript", "React"],
    ".ts": ["TypeScript"],
    ".tsx": ["TypeScript", "React"],
    ".html": ["HTML"],
    ".htm": ["HTML"],
    ".css": ["CSS"],
    ".scss": ["SCSS"],
    ".sass": ["SCSS"],
    ".sql": ["SQL"],
    ".php": ["PHP"],
    ".rb": ["Ruby"],
    ".go": ["Go"],
    ".rs": ["Rust"],
    ".cs": ["C#"],
    ".cpp": ["C++"],
    ".cc": ["C++"],
    ".cxx": ["C++"],
    ".c": ["C"],
    ".h": ["C"],
    ".kt": ["Kotlin"],
    ".kts": ["Kotlin"],
    ".vue": ["Vue"],
    ".md": [],  # docs only — not counted as primary language
}

SOURCE_CODE_EXTS = {e for e, langs in EXT_LANGUAGES.items() if langs}

# (pattern in file content or name, technology label, category, confidence)
MANIFEST_RULES: List[Tuple[str, str, str, str]] = [
    # package.json dependency keys (checked in joined deps text)
    (r"\breact\b", "React", "frameworks", "high"),
    (r"\bnext\b", "Next.js", "frameworks", "high"),
    (r"\bvite\b", "Vite", "build_tools", "high"),
    (r"\bvue\b", "Vue", "frameworks", "high"),
    (r"@angular/core|\bangular\b", "Angular", "frameworks", "high"),
    (r"\bexpress\b", "Express.js", "frameworks", "high"),
    (r"@nestjs/core|\bnestjs\b", "NestJS", "frameworks", "high"),
    (r"tailwindcss", "Tailwind CSS", "libraries", "high"),
    (r"\bbootstrap\b", "Bootstrap", "libraries", "high"),
    (r"\baxios\b", "Axios", "libraries", "high"),
    (r"\bprisma\b", "Prisma", "libraries", "high"),
    (r"\bmongoose\b", "MongoDB", "databases", "high"),
    (r"mysql2|\bmysql\b", "MySQL", "databases", "high"),
    (r"\bpg\b|postgres", "PostgreSQL", "databases", "high"),
    (r"sqlite3|better-sqlite3", "SQLite", "databases", "high"),
    (r"\bgraphql\b", "GraphQL", "libraries", "medium"),
]

POM_RULES: List[Tuple[str, str, str, str]] = [
    (r"spring-boot", "Spring Boot", "frameworks", "high"),
    (r"spring-web", "Spring Web", "frameworks", "high"),
    (r"spring-security", "Spring Security", "libraries", "high"),
    (r"mysql-connector|mysql", "MySQL", "databases", "high"),
    (r"postgresql", "PostgreSQL", "databases", "high"),
    (r"\bojdbc\b", "OracleDB", "databases", "high"),
    (r"\bh2\b", "H2 Database", "databases", "medium"),
    (r"<artifactId>maven", "Maven", "build_tools", "medium"),
]

PIP_RULES: List[Tuple[str, str, str, str]] = [
    (r"\bfastapi\b", "FastAPI", "frameworks", "high"),
    (r"\bflask\b", "Flask", "frameworks", "high"),
    (r"\bdjango\b", "Django", "frameworks", "high"),
    (r"\bpandas\b", "Pandas", "libraries", "high"),
    (r"\bnumpy\b", "NumPy", "libraries", "high"),
    (r"scikit-learn|sklearn", "Scikit-learn", "libraries", "high"),
    (r"\btensorflow\b", "TensorFlow", "libraries", "high"),
    (r"\btorch\b|pytorch", "PyTorch", "libraries", "high"),
    (r"\bsqlalchemy\b", "SQLAlchemy", "libraries", "high"),
    (r"psycopg2|psycopg", "PostgreSQL", "databases", "high"),
    (r"\bpymongo\b", "MongoDB", "databases", "high"),
]

FILE_SIGNATURE_RULES: List[Tuple[str, str, str, str]] = [
    ("Dockerfile", "Docker", "deployment", "high"),
    ("docker-compose.yml", "Docker Compose", "deployment", "high"),
    ("compose.yml", "Docker Compose", "deployment", "high"),
    ("tailwind.config.js", "Tailwind CSS", "libraries", "high"),
    ("tailwind.config.ts", "Tailwind CSS", "libraries", "high"),
    ("vite.config.js", "Vite", "build_tools", "high"),
    ("vite.config.ts", "Vite", "build_tools", "high"),
    ("next.config.js", "Next.js", "frameworks", "high"),
    ("next.config.ts", "Next.js", "frameworks", "high"),
    ("next.config.mjs", "Next.js", "frameworks", "high"),
    ("tsconfig.json", "TypeScript", "frameworks", "high"),
    (".env.example", "Environment Configuration", "libraries", "medium"),
    ("prisma/schema.prisma", "Prisma", "libraries", "high"),
    ("manage.py", "Django", "frameworks", "high"),
    ("pom.xml", "Maven", "build_tools", "high"),
    ("build.gradle", "Gradle", "build_tools", "high"),
    ("settings.gradle", "Gradle", "build_tools", "high"),
    ("go.mod", "Go modules", "package_managers", "high"),
    ("Cargo.toml", "Cargo", "package_managers", "high"),
    ("package.json", "npm", "package_managers", "high"),
    ("requirements.txt", "pip", "package_managers", "high"),
    ("pyproject.toml", "pip", "package_managers", "high"),
]


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace("\\", "/")


def _should_skip_dir(dirpath: str) -> bool:
    parts = set(dirpath.replace("\\", "/").split("/"))
    return bool(parts & SKIP_DIRS) or any(p.startswith(".") and p not in (".env.example",) for p in parts)


def _read_text(path: str, limit: int = 120_000) -> str:
    try:
        if os.path.getsize(path) > limit:
            return ""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _add_tech(
    store: Dict[str, Dict[str, Any]],
    name: str,
    category: str,
    evidence_path: str,
    confidence: str,
) -> None:
    if not name:
        return
    entry = store.setdefault(name, {
        "name": name,
        "category": category,
        "evidence": [],
        "confidence": confidence,
    })
    if evidence_path not in entry["evidence"]:
        entry["evidence"].append(evidence_path)
    # keep highest confidence
    rank = {"high": 3, "medium": 2, "low": 1}
    if rank.get(confidence, 0) > rank.get(entry["confidence"], 0):
        entry["confidence"] = confidence


def _apply_rules(
    text: str,
    rel_path: str,
    rules: List[Tuple[str, str, str, str]],
    store: Dict[str, Dict[str, Any]],
) -> None:
    low = text.lower()
    for pattern, label, category, conf in rules:
        if re.search(pattern, low, re.I):
            _add_tech(store, label, category, rel_path, conf)


def _scan_package_json(root: str, store: Dict[str, Dict[str, Any]]) -> None:
    found = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if _should_skip_dir(dirpath):
            continue
        if "package.json" not in files:
            continue
        path = os.path.join(dirpath, "package.json")
        rel = _rel(root, path)
        text = _read_text(path)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        dep_blob = " ".join(deps.keys()).lower()
        _add_tech(store, "npm", "package_managers", rel, "high")
        _apply_rules(dep_blob, rel, MANIFEST_RULES, store)
        found += 1
        if found >= 5:
            break


def _scan_pom(root: str, store: Dict[str, Dict[str, Any]]) -> None:
    for name in ("pom.xml",):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        rel = _rel(root, path)
        text = _read_text(path)
        _add_tech(store, "Maven", "build_tools", rel, "high")
        _add_tech(store, "Java", "languages", rel, "high")
        _apply_rules(text, rel, POM_RULES, store)


def _scan_gradle(root: str, store: Dict[str, Dict[str, Any]]) -> None:
    for name in ("build.gradle", "build.gradle.kts", "settings.gradle"):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        rel = _rel(root, path)
        text = _read_text(path)
        _add_tech(store, "Gradle", "build_tools", rel, "high")
        if "spring" in text.lower():
            _add_tech(store, "Spring Boot", "frameworks", rel, "high")
        if "kotlin" in text.lower() or name.endswith(".kts"):
            _add_tech(store, "Kotlin", "languages", rel, "medium")
        else:
            _add_tech(store, "Java", "languages", rel, "medium")


def _scan_python_manifests(root: str, store: Dict[str, Dict[str, Any]]) -> None:
    found = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if _should_skip_dir(dirpath):
            continue
        for name in ("requirements.txt", "pyproject.toml"):
            if name not in files:
                continue
            path = os.path.join(dirpath, name)
            rel = _rel(root, path)
            text = _read_text(path)
            _add_tech(store, "pip", "package_managers", rel, "high")
            _add_tech(store, "Python", "languages", rel, "high")
            _apply_rules(text, rel, PIP_RULES, store)
            found += 1
        if found >= 6:
            break


def _scan_fastapi_entrypoints(root: str, store: Dict[str, Dict[str, Any]]) -> None:
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if _should_skip_dir(dirpath):
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            if fn not in ("main.py", "app.py"):
                continue
            fp = os.path.join(dirpath, fn)
            rel = _rel(root, fp)
            head = _read_text(fp, 8000)
            if re.search(r"\bfrom\s+fastapi\b|\bimport\s+fastapi\b", head, re.I):
                _add_tech(store, "FastAPI", "frameworks", rel, "high")


def _scan_file_signatures(root: str, store: Dict[str, Dict[str, Any]]) -> None:
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if _should_skip_dir(dirpath):
            continue
        for fn in files:
            if fn in SKIP_FILES:
                continue
            fp = os.path.join(dirpath, fn)
            rel = _rel(root, fp)
            for sig, label, category, conf in FILE_SIGNATURE_RULES:
                if sig.startswith("."):
                    if fn == sig:
                        _add_tech(store, label, category, rel, conf)
                elif rel == sig or rel.endswith("/" + sig) or fn == sig:
                    _add_tech(store, label, category, rel, conf)


def _count_languages(root: str) -> Tuple[Dict[str, int], int]:
    counts: Dict[str, int] = defaultdict(int)
    total = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if _should_skip_dir(dirpath):
            continue
        for fn in files:
            if fn in SKIP_FILES:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in BINARY_OR_MEDIA_EXTS:
                continue
            langs = EXT_LANGUAGES.get(ext)
            if not langs:
                continue
            fp = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(fp) > 500_000:
                    continue
            except OSError:
                continue
            primary = langs[0]
            counts[primary] += 1
            total += 1
    return counts, total


def _language_percentages(counts: Dict[str, int], total: int) -> Dict[str, float]:
    if total <= 0:
        return {}
    return {lang: round((c / total) * 100, 1) for lang, c in sorted(counts.items(), key=lambda x: -x[1])}


def _top_level_folders(root: str, limit: int = 25) -> List[str]:
    out: List[str] = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if name.startswith(".") or name in SKIP_DIRS:
            continue
        full = os.path.join(root, name)
        if os.path.isdir(full):
            out.append(name + "/")
        else:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def validate_source_project(scan: Dict[str, Any]) -> Tuple[bool, str]:
    """Return (ok, message) for ZIP content validation."""
    stats = scan.get("scan_stats") or {}
    source_files = int(stats.get("source_files", 0))
    if source_files == 0:
        return False, "Uploaded ZIP does not appear to contain a valid source-code project."
    has_tech = bool(
        scan.get("languages")
        or scan.get("frameworks")
        or scan.get("package_managers")
    )
    if not has_tech:
        return False, "No clear tech stack detected. Please upload a valid source-code ZIP."
    return True, ""


def scan_tech_stack(project_path: str) -> Dict[str, Any]:
    """
    Scan extracted project directory and return structured tech-stack JSON.
    """
    if not os.path.exists(project_path):
        return {"valid": False, "error": "Path does not exist", "scan_stats": {"source_files": 0}}

    root = project_path if os.path.isdir(project_path) else os.path.dirname(project_path)
    tech_store: Dict[str, Dict[str, Any]] = {}

    _scan_package_json(root, tech_store)
    _scan_pom(root, tech_store)
    _scan_gradle(root, tech_store)
    _scan_python_manifests(root, tech_store)
    _scan_fastapi_entrypoints(root, tech_store)
    _scan_file_signatures(root, tech_store)

    lang_counts, source_files = _count_languages(root)
    lang_pcts = _language_percentages(lang_counts, source_files)

    for lang in lang_counts:
        _add_tech(tech_store, lang, "languages", f"file extensions ({lang_counts[lang]} files)", "high")

    categories = {
        "languages": [],
        "frameworks": [],
        "libraries": [],
        "databases": [],
        "build_tools": [],
        "deployment": [],
        "package_managers": [],
    }
    evidence: Dict[str, List[str]] = {}
    confidence: Dict[str, str] = {}

    for name, meta in sorted(tech_store.items()):
        cat = meta["category"]
        if cat in categories and name not in categories[cat]:
            categories[cat].append(name)
        evidence[name] = meta["evidence"][:8]
        confidence[name] = meta["confidence"]

    result: Dict[str, Any] = {
        "languages": categories["languages"],
        "frameworks": categories["frameworks"],
        "libraries": categories["libraries"],
        "databases": categories["databases"],
        "build_tools": categories["build_tools"],
        "deployment": categories["deployment"],
        "package_managers": categories["package_managers"],
        "language_percentages": lang_pcts,
        "evidence": evidence,
        "confidence": confidence,
        "folder_structure": _top_level_folders(root),
        "scan_stats": {
            "source_files": source_files,
            "technologies_detected": len(tech_store),
        },
    }

    ok, msg = validate_source_project(result)
    result["valid"] = ok
    if not ok:
        result["validation_message"] = msg
    return result


def tech_stack_to_detected_stack(tech: Dict[str, Any]) -> Dict[str, str]:
    """Map scanner output to legacy detected_stack flat dict for merge/UI."""
    langs = tech.get("languages") or []
    frameworks = tech.get("frameworks") or []
    databases = tech.get("databases") or []
    deployment = tech.get("deployment") or []

    frontend_kw = {"react", "next.js", "vue", "angular", "vite", "tailwind", "bootstrap", "typescript"}
    backend_kw = {"express", "fastapi", "django", "flask", "spring", "nest", "gradle", "java", "go"}

    frontend = [f for f in frameworks + langs if any(k in f.lower() for k in frontend_kw)]
    backend = [f for f in frameworks + langs if any(k in f.lower() for k in backend_kw)]

    return {
        "frontend": ", ".join(frontend[:3]) or "",
        "backend": ", ".join(backend[:3]) or "",
        "database": ", ".join(databases[:3]) or "",
        "authentication": "",
        "deployment": deployment,
        "api_style": "REST" if backend else "",
    }
