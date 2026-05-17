"""
Central FastAPI exception handlers for API-key and related LLM failures.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agents.api_errors import ApiKeyError

logger = logging.getLogger("architect_ai.api")


def _api_key_payload(exc: ApiKeyError) -> dict:
    return {
        "error": True,
        "error_type": exc.error_type,
        "message": exc.message,
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiKeyError)
    async def handle_api_key_error(_request: Request, exc: ApiKeyError) -> JSONResponse:
        logger.warning("API key error [%s]: %s", exc.error_type, exc.message)
        print(f"[API] {exc.error_type}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=_api_key_payload(exc),
        )
