"""
Shared Groq LLM helpers — key rotation, token limits, usage logging.
"""

import os
from typing import List, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from agents.api_errors import (
    GROQ_DEFAULT_MODEL,
    ApiKeyError,
    classify_llm_error,
    mask_key,
    normalize_api_key,
)
from agents.llm_context import get_runtime_groq_keys

load_dotenv()

# Token-saving: cap completion size per call type (Groq ~12k context budget).
MAX_TOKENS_NARRATIVE = 1200
MAX_TOKENS_STRUCTURED = 2200
MAX_TOKENS_GREENFIELD = 2000
MAX_TOKENS_BROWNFIELD = 2800


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate_limit" in text or "rate limit" in text


def _log_token_usage(response, label: str = "") -> None:
    """Log token counts when provider returns them; never log prompt content."""
    meta = getattr(response, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}
    if not usage and hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = response.usage_metadata
    if usage:
        prompt_t = usage.get("prompt_tokens") or usage.get("input_tokens")
        completion_t = usage.get("completion_tokens") or usage.get("output_tokens")
        total_t = usage.get("total_tokens") or usage.get("total")
        print(
            f"[LLM tokens]{f' {label}' if label else ''} "
            f"prompt={prompt_t} completion={completion_t} total={total_t}"
        )


def _raise_classified(exc: Exception) -> None:
    classified = classify_llm_error(exc)
    if classified:
        keys = groq_keys()
        print(
            f"[LLM] {classified.error_type}: {classified.message} "
            f"(key={mask_key(keys[0]) if keys else 'none'})"
        )
        raise classified from exc
    raise exc


def groq_keys() -> List[str]:
    runtime = get_runtime_groq_keys()
    if runtime:
        return [k for k in runtime if k]
    keys: List[str] = []
    for env_name in ("GROQ_API_KEY", "GROQ_API_KEY1", "GROQ_API_KEY2"):
        raw = os.getenv(env_name)
        if not raw:
            continue
        normalized = normalize_api_key(raw)
        if normalized:
            keys.append(normalized)
    return keys


def get_llm(*, max_tokens: Optional[int] = None) -> ChatGroq:
    keys = groq_keys()
    if not keys:
        raise ApiKeyError(
            "API_KEY_MISSING",
            "No GROQ_API_KEY configured. Set GROQ_API_KEY (or GROQ_API_KEY1/2) in .env.",
            503,
        )
    kwargs = {"model": GROQ_DEFAULT_MODEL, "groq_api_key": keys[0]}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    print(f"[LLM] Using Groq key {mask_key(keys[0])} model={GROQ_DEFAULT_MODEL} max_tokens={max_tokens}")
    return ChatGroq(**kwargs)


def invoke_with_fallback(prompt: str, *, max_tokens: int = MAX_TOKENS_NARRATIVE, label: str = "") -> str:
    """Try each Groq key; skip to next on 429."""
    keys = groq_keys()
    if not keys:
        raise ApiKeyError(
            "API_KEY_MISSING",
            "No GROQ_API_KEY configured in environment.",
            503,
        )
    last_err: Exception | None = None
    for key in keys:
        try:
            llm = ChatGroq(model=GROQ_DEFAULT_MODEL, groq_api_key=key, max_tokens=max_tokens)
            response = llm.invoke(prompt)
            _log_token_usage(response, label)
            return (response.content or "").strip()
        except Exception as e:
            if _is_rate_limit(e):
                last_err = e
                continue
            _raise_classified(e)
    if last_err is not None:
        _raise_classified(last_err)
    raise ApiKeyError(
        "API_KEY_EXHAUSTED",
        "API token limit reached. Please update the API key.",
        402,
    )


def structured_invoke(llm: ChatGroq, schema, prompt: str, *, label: str = ""):
    """Structured output with key fallback on rate limits."""
    keys = groq_keys()
    if not keys:
        raise ApiKeyError(
            "API_KEY_MISSING",
            "No GROQ_API_KEY configured in environment.",
            503,
        )
    max_tokens = getattr(llm, "max_tokens", None) or MAX_TOKENS_STRUCTURED
    last_err: Exception | None = None
    for key in keys:
        try:
            client = ChatGroq(model=GROQ_DEFAULT_MODEL, groq_api_key=key, max_tokens=max_tokens)
            structured = client.with_structured_output(schema)
            response = structured.invoke(prompt)
            if hasattr(response, "response_metadata"):
                _log_token_usage(response, label)
            return response
        except Exception as e:
            if _is_rate_limit(e):
                last_err = e
                continue
            _raise_classified(e)
    if last_err is not None:
        _raise_classified(last_err)
    raise ApiKeyError(
        "API_KEY_EXHAUSTED",
        "API token limit reached. Please update the API key.",
        402,
    )
