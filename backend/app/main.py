import os
import tempfile
import zipfile
from typing import List, Optional

from fastapi import File, Request, UploadFile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

from langchain_groq import ChatGroq

from agents.api_errors import (
    GROQ_DEFAULT_MODEL,
    ApiKeyError,
    classify_llm_error,
    mask_key,
    normalize_api_key,
    reraise_if_api_key_error,
)
from agents.llm_context import set_runtime_groq_keys
from agents.llm_utils import groq_keys, invoke_with_fallback

from .error_handlers import register_error_handlers

from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BrownfieldRequest,
    GreenfieldRequest,
    MemoryForgetRequest,
    MemoryTrainRequest,
    ModifyArchitectureRequest,
    ModifyArchitectureResponse,
    RequirementsCompileRequest,
    RequirementsCompileResponse,
)
from .service import (
    compile_requirements,
    forget_memory_by_path,
    run_analysis,
    run_modify_architecture,
    train_memory_from_path,
)


def _split_origins(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _load_env() -> None:
    # `main.py` is at architect-ai/backend/app/ — repo root is architect-ai/
    this_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(this_dir, "..", ".."))
    load_dotenv(os.path.join(repo_root, ".env"), override=False)


_load_env()


app = FastAPI(
    title="Autonomous Architecture Planning API",
    version="1.0.0",
    description="FastAPI backend for Greenfield/Brownfield agent workflows.",
)

allowed_origins = _split_origins(
    os.getenv(
        "CORS_ORIGINS",
        # Common dev ports; include 127.0.0.1 — browsers treat it as a distinct origin from localhost.
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8080,http://127.0.0.1:8080",
    )
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)


@app.middleware("http")
async def groq_key_from_header(request: Request, call_next):
    """Optional per-request key via X-Groq-Api-Key (overrides .env for that request)."""
    header_key = normalize_api_key(request.headers.get("x-groq-api-key"))
    if header_key:
        set_runtime_groq_keys([header_key])
        print(f"[API] {request.method} {request.url.path} — header key {mask_key(header_key)}")
    try:
        return await call_next(request)
    finally:
        if header_key:
            set_runtime_groq_keys(None)


class ApiKeyValidateRequest(BaseModel):
    api_key: Optional[str] = None


def _handle_route_error(exc: Exception, fallback_message: str) -> None:
    """Log, classify API-key failures, or raise HTTP 500 for other errors."""
    if isinstance(exc, ApiKeyError):
        raise exc
    try:
        reraise_if_api_key_error(exc)
    except ApiKeyError:
        raise
    print(f"[API] {fallback_message}: {exc}")
    raise HTTPException(status_code=500, detail=f"{fallback_message}: {exc}") from exc


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/api-key/status")
def api_key_status():
    """
    Lightweight status for the UI — does not call the LLM (no quota spent).
    """
    keys = groq_keys()
    if not keys:
        return {
            "status": "missing",
            "error_type": "API_KEY_MISSING",
            "message": "No GROQ_API_KEY configured in backend .env.",
            "key_count": 0,
            "provider": "groq",
            "model": GROQ_DEFAULT_MODEL,
        }
    return {
        "status": "configured",
        "message": f"{len(keys)} Groq API key(s) loaded (env or request header).",
        "key_count": len(keys),
        "provider": "groq",
        "model": GROQ_DEFAULT_MODEL,
        "masked_key": mask_key(keys[0]),
    }


@app.post("/api/api-key/validate")
def validate_api_key(payload: ApiKeyValidateRequest = ApiKeyValidateRequest()):
    """
    Real Groq validation — one minimal completion. Does not log the full key.
    """
    body_key = normalize_api_key(payload.api_key) if payload.api_key else ""
    if body_key:
        set_runtime_groq_keys([body_key])

    keys = groq_keys()
    if not keys:
        return {
            "valid": False,
            "error_type": "API_KEY_MISSING",
            "message": "No API key provided. Set GROQ_API_KEY in .env or send api_key in the request body.",
            "provider": "groq",
            "model": GROQ_DEFAULT_MODEL,
        }

    key = keys[0]
    print(f"[API] validate — provider=groq model={GROQ_DEFAULT_MODEL} key={mask_key(key)}")
    try:
        llm = ChatGroq(model=GROQ_DEFAULT_MODEL, groq_api_key=key)
        response = llm.invoke("Reply with exactly: OK")
        preview = ((response.content or "").strip())[:40]
        return {
            "valid": True,
            "provider": "groq",
            "model": GROQ_DEFAULT_MODEL,
            "message": "API key is valid and accepted by Groq.",
            "masked_key": mask_key(key),
            "preview": preview,
        }
    except Exception as exc:
        classified = classify_llm_error(exc)
        if classified:
            print(f"[API] validate failed — {classified.error_type}: {classified.message}")
            return {
                "valid": False,
                "error_type": classified.error_type,
                "message": classified.message,
                "provider": "groq",
                "model": GROQ_DEFAULT_MODEL,
                "masked_key": mask_key(key),
            }
        print(f"[API] validate failed — unclassified: {type(exc).__name__}: {exc}")
        return {
            "valid": False,
            "error_type": "PROVIDER_ERROR",
            "message": str(exc)[:300],
            "provider": "groq",
            "model": GROQ_DEFAULT_MODEL,
            "masked_key": mask_key(key),
        }
    finally:
        if body_key:
            set_runtime_groq_keys(None)


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    try:
        result = run_analysis(
            payload.mode,
            payload.input,
            project_name=payload.project_name,
            scalability=payload.scalability,
            performance=payload.performance,
            maintainability=payload.maintainability,
            security=payload.security,
            expected_users=payload.expected_users,
            growth_rate=payload.growth_rate,
        )
        return AnalyzeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ApiKeyError:
        raise
    except Exception as exc:
        _handle_route_error(exc, "Analysis failed")


# Backwards-compatible aliases (no /api prefix)
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_alias(payload: AnalyzeRequest):
    return analyze(payload)


@app.post("/api/greenfield", response_model=AnalyzeResponse)
def greenfield(payload: GreenfieldRequest):
    try:
        result = run_analysis(
            "greenfield",
            payload.requirements,
            project_name=payload.project_name,
            scalability=payload.scalability,
            performance=payload.performance,
            maintainability=payload.maintainability,
            security=payload.security,
            expected_users=payload.expected_users,
            growth_rate=payload.growth_rate,
        )
        return AnalyzeResponse(**result)
    except ApiKeyError:
        raise
    except Exception as exc:
        _handle_route_error(exc, "Greenfield failed")


@app.post("/greenfield", response_model=AnalyzeResponse)
def greenfield_alias(payload: GreenfieldRequest):
    return greenfield(payload)


@app.post("/api/brownfield", response_model=AnalyzeResponse)
def brownfield(payload: BrownfieldRequest):
    try:
        result = run_analysis("brownfield", payload.input)
        return AnalyzeResponse(**result)
    except ApiKeyError:
        raise
    except Exception as exc:
        _handle_route_error(exc, "Brownfield failed")


@app.post("/brownfield", response_model=AnalyzeResponse)
def brownfield_alias(payload: BrownfieldRequest):
    return brownfield(payload)


def _safe_extract_zip(zip_path: str, extract_dir: str) -> None:
    """
    Prevent Zip Slip by ensuring all extracted paths stay within extract_dir.
    """
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            # Skip directories implicitly handled by ZipFile
            member_path = os.path.normpath(member.filename)
            if os.path.isabs(member_path) or member_path.startswith(".."):
                raise ValueError("Unsafe zip entry path.")
            dest_path = os.path.normpath(os.path.join(extract_dir, member_path))
            if not dest_path.startswith(os.path.normpath(extract_dir)):
                raise ValueError("Unsafe zip entry path.")
        zf.extractall(extract_dir)


@app.post("/api/brownfield/zip", response_model=AnalyzeResponse)
async def brownfield_zip(file: UploadFile = File(...)):
    """
    Upload a .zip of a codebase, extract to a temp folder, and run brownfield analysis.
    """
    filename = (file.filename or "").lower()
    if not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file.")

    try:
        with tempfile.TemporaryDirectory(prefix="architect_ai_zip_") as td:
            zip_path = os.path.join(td, "codebase.zip")
            content = await file.read()
            with open(zip_path, "wb") as wf:
                wf.write(content)

            extract_dir = os.path.join(td, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            _safe_extract_zip(zip_path, extract_dir)

            # If zip contains a single top-level folder, analyze that folder.
            entries = [e for e in os.listdir(extract_dir) if e and not e.startswith(".")]
            root = extract_dir
            if len(entries) == 1:
                candidate = os.path.join(extract_dir, entries[0])
                if os.path.isdir(candidate):
                    root = candidate

            result = run_analysis("brownfield", root)
            return AnalyzeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid zip file.") from exc
    except ApiKeyError:
        raise
    except Exception as exc:
        _handle_route_error(exc, "Brownfield zip failed")


@app.post("/api/memory/train")
def train_memory(payload: MemoryTrainRequest):
    ok, message = train_memory_from_path(payload.path)
    if not ok:
        raise HTTPException(status_code=500, detail=message)
    return {"status": "ok", "message": message}


@app.post("/api/memory/forget")
def forget_memory(payload: MemoryForgetRequest):
    ok, message = forget_memory_by_path(payload.path)
    if not ok:
        raise HTTPException(status_code=500, detail=message)
    return {"status": "ok", "message": message}


class NfrSuggestRequest(BaseModel):
    prompt: str
    scalability: int = 50
    performance: int = 50
    maintainability: int = 50
    security: int = 50


class NfrSuggestResponse(BaseModel):
    improved_prompt: str
    suggestions: list[str]
    reasoning: str


@app.get("/api/templates")
def list_templates():
    from agents.greenfield_templates import list_templates as _list

    return {"templates": _list()}


@app.get("/api/templates/{template_id}")
def get_template(template_id: str):
    from agents.greenfield_templates import get_template as _get

    tpl = _get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": template_id, **tpl}


@app.post("/api/requirements/compile", response_model=RequirementsCompileResponse)
def requirements_compile(payload: RequirementsCompileRequest):
    try:
        result = compile_requirements(
            payload.source,
            template_id=payload.template_id,
            answers=payload.answers,
            overrides=payload.overrides,
        )
        return RequirementsCompileResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ApiKeyError:
        raise
    except Exception as exc:
        _handle_route_error(exc, "Compile failed")


@app.post("/api/modify-architecture", response_model=ModifyArchitectureResponse)
@app.post("/modify-architecture", response_model=ModifyArchitectureResponse)
def modify_architecture_route(payload: ModifyArchitectureRequest):
    try:
        result = run_modify_architecture(
            payload.mode,
            payload.current_architecture,
            payload.user_change_request,
        )
        return ModifyArchitectureResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ApiKeyError:
        raise
    except Exception as exc:
        _handle_route_error(exc, "Modification failed")


@app.post("/api/suggest-nfr", response_model=NfrSuggestResponse)
def suggest_nfr(payload: NfrSuggestRequest):
    """
    Use Groq (llama-3.3-70b) to analyze the user's functional requirements prompt
    and NFR slider values and suggest concrete improvements.
    """
    import re as _re

    nfr_context = (
        f"- Scalability priority: {payload.scalability}/100\n"
        f"- Performance priority: {payload.performance}/100\n"
        f"- Maintainability priority: {payload.maintainability}/100\n"
        f"- Security priority: {payload.security}/100"
    )

    prompt_text = (
        "You are a senior software architect helping a developer write better project "
        "requirement prompts for an AI architecture planning tool.\n\n"
        "The user has written the following functional requirements prompt:\n"
        "---\n"
        f"{payload.prompt}\n"
        "---\n\n"
        "They have also set these non-functional requirement priorities:\n"
        f"{nfr_context}\n\n"
        "Your job is to:\n"
        "1. Analyze the prompt and identify what is vague, missing, or ambiguous.\n"
        "2. Suggest a concise list of concrete improvements (3-5 bullet points).\n"
        "3. Generate an improved, enriched version of their original prompt that "
        "incorporates the NFR priorities and fills any gaps.\n\n"
        "Return your response STRICTLY in the following format (use these exact headers):\n\n"
        "### Improved Prompt\n"
        "<the improved, rewritten prompt here - keep it as a single paragraph>\n\n"
        "### Suggestions\n"
        "- <suggestion 1>\n"
        "- <suggestion 2>\n"
        "- <suggestion 3>\n\n"
        "### Reasoning\n"
        "<1-2 sentences explaining why these changes make the prompt better>\n"
    )

    try:
        text = invoke_with_fallback(prompt_text)

        improved_prompt = ""
        suggestions = []
        reasoning = ""

        imp_match = _re.search(r"### Improved Prompt\n([\s\S]*?)(?=###|$)", text)
        sug_match = _re.search(r"### Suggestions\n([\s\S]*?)(?=###|$)", text)
        rea_match = _re.search(r"### Reasoning\n([\s\S]*?)(?=###|$)", text)

        if imp_match:
            improved_prompt = imp_match.group(1).strip()
        if sug_match:
            raw_sug = sug_match.group(1).strip()
            suggestions = [s.lstrip("- ").strip() for s in raw_sug.splitlines() if s.strip().startswith("-")]
        if rea_match:
            reasoning = rea_match.group(1).strip()

        if not improved_prompt:
            improved_prompt = payload.prompt
        if not suggestions:
            suggestions = [
                "Add specific technology stack constraints (e.g., language, framework).",
                "Specify the expected scale, load, or number of concurrent users.",
                "Clarify integration requirements with external systems or APIs.",
            ]
        if not reasoning:
            reasoning = "The improved prompt gives the architecture agent more concrete context to produce a grounded plan."

        return NfrSuggestResponse(
            improved_prompt=improved_prompt,
            suggestions=suggestions,
            reasoning=reasoning,
        )

    except ApiKeyError:
        raise
    except Exception as exc:
        _handle_route_error(exc, "Prompt suggestion failed")


