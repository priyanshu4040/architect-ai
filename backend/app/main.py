import os
import tempfile
import zipfile
from typing import List

from fastapi import File, UploadFile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BrownfieldRequest,
    GreenfieldRequest,
    MemoryForgetRequest,
    MemoryTrainRequest,
)
from .service import forget_memory_by_path, run_analysis, train_memory_from_path


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


@app.get("/health")
def health_check():
    return {"status": "ok"}


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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Greenfield failed: {exc}") from exc


@app.post("/greenfield", response_model=AnalyzeResponse)
def greenfield_alias(payload: GreenfieldRequest):
    return greenfield(payload)


@app.post("/api/brownfield", response_model=AnalyzeResponse)
def brownfield(payload: BrownfieldRequest):
    try:
        result = run_analysis("brownfield", payload.input)
        return AnalyzeResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Brownfield failed: {exc}") from exc


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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Brownfield zip failed: {exc}") from exc


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


@app.post("/api/suggest-nfr", response_model=NfrSuggestResponse)
def suggest_nfr(payload: NfrSuggestRequest):
    """
    Use Groq (llama-3.3-70b) to analyze the user's functional requirements prompt
    and NFR slider values and suggest concrete improvements.
    """
    import re as _re
    from langchain_groq import ChatGroq

    # Try both GROQ keys with fallback
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY1")
    if not groq_key:
        raise HTTPException(status_code=500, detail="No GROQ_API_KEY configured.")

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
        llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_key)
        response = llm.invoke(prompt_text)
        text = (response.content or "").strip()

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

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prompt suggestion failed: {exc}") from exc


