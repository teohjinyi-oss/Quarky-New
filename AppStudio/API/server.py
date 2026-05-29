"""
Quarky_Ai — REST API Server

FastAPI application with CORS, SSE streaming, and auto-detect local/network auth.
Startup initializes all background systems. Shutdown cleans up gracefully.
"""

import os
import threading
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


# ─── Auth Middleware ─────────────────────────────────────────

_API_KEY: str = os.environ.get("QUARKY_API_KEY", "")


def _is_local(request: Request) -> bool:
    """Check if request originates from localhost."""
    client = request.client
    if client is None:
        return True
    host = client.host
    return host in ("127.0.0.1", "::1", "localhost", "testclient")


# ─── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    # Startup
    try:
        from MAIINNN.Memory.manager import start_decay_engine
        start_decay_engine()
    except Exception:
        pass

    try:
        from MAIINNN.Functions.action.registry import ensure_builtins
        ensure_builtins()
    except Exception:
        pass

    try:
        from MAIINNN.Functions.action.app_discovery import refresh
        refresh()
    except Exception:
        pass

    yield

    # Shutdown
    try:
        from MAIINNN.Memory.manager import stop_decay_engine
        stop_decay_engine()
    except Exception:
        pass


# ─── App ─────────────────────────────────────────────────────

app = FastAPI(
    title="Quarky AI",
    description="Zero-LLM Personal AI Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — localhost open by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth Dependency ─────────────────────────────────────────

from fastapi import HTTPException


async def verify_auth(request: Request) -> None:
    """
    Localhost requests bypass auth.
    Network requests require X-API-Key header matching QUARKY_API_KEY env var.
    """
    if _is_local(request):
        return

    if not _API_KEY:
        raise HTTPException(403, "API key not configured for network access")

    key = request.headers.get("X-API-Key", "")
    if not key or key != _API_KEY:
        raise HTTPException(401, "Invalid or missing API key")


# ─── Register Routes ─────────────────────────────────────────

from AppStudio.API.routes import router
app.include_router(router)
