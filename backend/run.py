"""
Uvicorn launcher for the Architect-AI backend.

Run from the project root:
    python backend/run.py

Or with custom host/port via environment variables:
    HOST=0.0.0.0 PORT=8080 python backend/run.py
"""

import os
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `agents.*` imports resolve correctly.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() in {"1", "true", "yes"}

    print(f"Starting Architect-AI backend on http://{host}:{port}")
    print(f"  Swagger UI -> http://{host}:{port}/docs")
    print(f"  ReDoc      -> http://{host}:{port}/redoc")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=reload,
    )
