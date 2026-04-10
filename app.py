"""
Root ASGI entrypoint for running the FastAPI backend.

Run:
  python -m uvicorn app:app --reload --port 8000
"""

from backend.app.main import app

