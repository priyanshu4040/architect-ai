"""
Per-request Groq API key override (optional X-Groq-Api-Key header).
Falls back to GROQ_API_KEY* environment variables when unset.
"""

from contextvars import ContextVar
from typing import List, Optional

_runtime_keys: ContextVar[Optional[List[str]]] = ContextVar("runtime_groq_keys", default=None)


def set_runtime_groq_keys(keys: Optional[List[str]]) -> None:
    _runtime_keys.set(keys if keys else None)


def get_runtime_groq_keys() -> Optional[List[str]]:
    return _runtime_keys.get()
