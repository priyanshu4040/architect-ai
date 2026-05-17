"""
Classify Groq / LLM failures into structured API-key errors for the FastAPI layer.
Uses provider SDK types first; avoids broad substring false positives.
"""

from __future__ import annotations

import re
from typing import Any, Optional

# Default Groq chat model for this project
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"


class ApiKeyError(Exception):
    """Raised when an LLM call fails due to API key, quota, model, or provider limits."""

    def __init__(self, error_type: str, message: str, status_code: int = 402):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.status_code = status_code


def mask_key(key: str | None) -> str:
    if not key:
        return ""
    k = key.strip()
    if len(k) <= 10:
        return "gsk_****"
    return f"{k[:6]}...{k[-4:]}"


def normalize_api_key(key: str | None) -> str:
    if not key:
        return ""
    k = key.strip()
    if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
        k = k[1:-1].strip()
    return k


def _exception_text(exc: Exception) -> str:
    parts: list[str] = [str(exc)]
    for attr in ("message", "body", "text"):
        val = getattr(exc, attr, None)
        if val is not None:
            parts.append(str(val))
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            parts.append(str(getattr(response, "text", "") or ""))
        except Exception:
            pass
    status = getattr(exc, "status_code", None)
    if status is not None:
        parts.append(str(status))
    return " ".join(parts).lower()


def _status_code(exc: Exception) -> int | None:
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    response = getattr(exc, "response", None)
    if response is not None:
        sc = getattr(response, "status_code", None)
        if isinstance(sc, int):
            return sc
    return None


def _is_rate_limit_text(text: str) -> bool:
    return (
        "429" in text
        or "rate_limit" in text
        or "rate limit" in text
        or "too many requests" in text
        or "rate_limit_exceeded" in text
    )


def _is_invalid_key_text(text: str) -> bool:
    """Strict patterns — do not match generic 'authentication' in prompts."""
    patterns = (
        r"invalid\s+api\s+key",
        r"invalid_api_key",
        r"incorrect\s+api\s+key",
        r"invalid\s+x-api-key",
        r"api\s+key\s+is\s+invalid",
        r"authentication\s+failed",
        r"auth(?:entication)?\s+error.*api\s+key",
    )
    return any(re.search(p, text) for p in patterns)


def _is_model_error_text(text: str) -> bool:
    if "model" not in text:
        return False
    return any(
        m in text
        for m in (
            "not found",
            "does not exist",
            "decommissioned",
            "deprecated",
            "unknown model",
            "model_not_found",
            "invalid model",
        )
    )


def _classify_groq_sdk(exc: Exception) -> Optional[ApiKeyError]:
    try:
        from groq import APIStatusError, AuthenticationError, PermissionDeniedError, RateLimitError
    except ImportError:
        return None

    if isinstance(exc, AuthenticationError):
        return ApiKeyError(
            "API_KEY_INVALID",
            "The API key was rejected by Groq. Check GROQ_API_KEY in .env (no extra spaces or quotes).",
            401,
        )
    if isinstance(exc, PermissionDeniedError):
        return ApiKeyError(
            "API_PERMISSION_DENIED",
            "The API key is valid but lacks permission for this operation.",
            403,
        )
    if isinstance(exc, RateLimitError):
        return ApiKeyError(
            "API_RATE_LIMIT",
            "API rate limit exceeded. Your key is likely valid — wait and retry or use another key.",
            429,
        )
    if isinstance(exc, APIStatusError):
        status = _status_code(exc) or 500
        text = _exception_text(exc)
        if status == 401 and _is_invalid_key_text(text):
            return ApiKeyError(
                "API_KEY_INVALID",
                "The API key was rejected by Groq.",
                401,
            )
        if status == 429 or _is_rate_limit_text(text):
            return ApiKeyError(
                "API_RATE_LIMIT",
                "API rate limit exceeded. Your key may still be valid.",
                429,
            )
        if _is_model_error_text(text) or (status == 404 and "model" in text):
            return ApiKeyError(
                "INVALID_MODEL",
                f"The model '{GROQ_DEFAULT_MODEL}' is unavailable. Check Groq model name in backend config.",
                400,
            )
        if status in (402, 403) and any(
            m in text for m in ("quota", "billing", "credit", "insufficient")
        ):
            return ApiKeyError(
                "API_KEY_EXHAUSTED",
                "API key is valid, but quota or billing limit is exhausted.",
                402,
            )
    return None


def classify_llm_error(exc: Exception) -> Optional[ApiKeyError]:
    """Map provider exceptions to ApiKeyError, or return None if unrelated."""
    if isinstance(exc, ApiKeyError):
        return exc

    sdk = _classify_groq_sdk(exc)
    if sdk:
        return sdk

    text = _exception_text(exc)
    status = _status_code(exc)

    if "no groq_api_key" in text or ("not configured" in text and "groq" in text):
        return ApiKeyError(
            "API_KEY_MISSING",
            "No GROQ_API_KEY configured. Set GROQ_API_KEY in the project root .env and restart the backend.",
            503,
        )

    if _is_model_error_text(text):
        return ApiKeyError(
            "INVALID_MODEL",
            f"Model error from Groq (configured: {GROQ_DEFAULT_MODEL}).",
            400,
        )

    if status == 429 or _is_rate_limit_text(text):
        return ApiKeyError(
            "API_RATE_LIMIT",
            "API rate limit exceeded. Your key may still be valid — try again later.",
            429,
        )

    if any(
        m in text
        for m in (
            "quota",
            "insufficient_quota",
            "billing",
            "credit",
            "exhausted",
            "usage limit",
            "tokens per day",
            "tokens per minute",
        )
    ):
        return ApiKeyError(
            "API_KEY_EXHAUSTED",
            "API key is valid, but quota or token limit is exhausted.",
            402,
        )

    if _is_invalid_key_text(text):
        return ApiKeyError(
            "API_KEY_INVALID",
            "The API key was rejected by Groq.",
            401,
        )

    if status == 401 and any(m in text for m in ("invalid", "unauthorized", "api key")):
        return ApiKeyError(
            "API_KEY_INVALID",
            "The API key was rejected by Groq.",
            401,
        )

    if any(m in text for m in ("connection", "timeout", "network", "refused", "unreachable")):
        return ApiKeyError(
            "PROVIDER_UNREACHABLE",
            "Could not reach Groq. Check network and backend connectivity.",
            503,
        )

    return None


def reraise_if_api_key_error(exc: Exception) -> None:
    """Re-raise as ApiKeyError when the underlying failure is key/quota related."""
    if isinstance(exc, ApiKeyError):
        raise exc
    classified = classify_llm_error(exc)
    if classified:
        raise classified from exc
