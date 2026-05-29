"""
Quarky_Ai — API Routes

All REST endpoints:
  POST /chat             — Process text, return response + metadata
  POST /chat/stream      — SSE streaming response
  POST /chat/confirm     — Execute a confirmed action
  GET  /health           — System health check
  GET  /memory/stats     — Memory layer counts
  GET  /memory/search    — Cross-layer keyword search
  DELETE /memory/{layer}/{id} — Forget a memory entry
  POST /memory/permanent — Force-store to permanent memory
  GET  /actions/recent   — Recent action log
  GET  /actions/stats    — Action statistics
  POST /actions/undo     — Undo last reversible action
  GET  /system/status    — Full system dashboard
  GET  /system/config    — Current config values
  POST /system/app       — Register custom app
  GET  /integrations/status — Connected providers
  GET  /integrations/emails — Fetch recent emails
  GET  /integrations/events — Fetch upcoming calendar events
"""

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from AppStudio.API.server import verify_auth


router = APIRouter(dependencies=[Depends(verify_auth)])


# ─── Request/Response Models ─────────────────────────────────

class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    response: str
    metadata: dict[str, Any] = {}


class ConfirmRequest(BaseModel):
    action_type: str
    command: str
    target: str
    risk_level: str
    parameters: dict[str, Any] = {}


class MemoryStoreRequest(BaseModel):
    text: str = Field(..., min_length=1)
    tags: list[str] = []


class AppRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)


# ─── Chat ────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Process text through the full brain pipeline."""
    from MAIINNN.Decision.output_gate import process

    result = await asyncio.to_thread(process, req.text)

    metadata: dict[str, Any] = {
        "source": result.source,
        "confidence": result.confidence,
        "memory_actions": result.memory_actions,
        "reasoning": result.reasoning,
    }

    if result.action_request:
        ar = result.action_request
        metadata["action_request"] = {
            "action_type": ar.action_type,
            "target": ar.target,
            "risk_level": ar.risk_level,
            "needs_confirmation": ar.needs_confirmation,
        }

    if result.action_result:
        metadata["action_result"] = {
            "success": result.action_result.success,
            "message": result.action_result.message,
        }

    return ChatResponse(response=result.response, metadata=metadata)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """SSE streaming response."""
    async def generate():
        from MAIINNN.Decision.output_gate import process

        # Send thinking event
        yield f"data: {json.dumps({'type': 'thinking', 'text': 'Processing...'})}\n\n"

        result = await asyncio.to_thread(process, req.text)

        # Stream the response in chunks
        response_text = result.response
        chunk_size = 20
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
            await asyncio.sleep(0.03)

        # Send metadata
        metadata: dict[str, Any] = {
            "source": result.source,
            "confidence": result.confidence,
        }
        yield f"data: {json.dumps({'type': 'metadata', 'data': metadata})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/confirm")
async def chat_confirm(req: ConfirmRequest) -> dict[str, Any]:
    """Execute a previously-confirmed action."""
    from MAIINNN.Decision.action_resolver import ActionRequest
    from MAIINNN.Decision.output_gate import confirm_action

    action_request = ActionRequest(
        action_type=req.action_type,
        command=req.command,
        target=req.target,
        risk_level=req.risk_level,
        parameters=req.parameters,
        needs_confirmation=True,
    )

    result = await asyncio.to_thread(confirm_action, action_request)
    return {
        "success": result.success,
        "message": result.message,
    }


# ─── Health ──────────────────────────────────────────────────

@router.get("/health")
async def health() -> dict[str, Any]:
    """System health with subsystem status from orchestrator heartbeat."""
    from AppStudio.Config import VERSION, CHANNEL
    basic: dict[str, Any] = {
        "status": "ok",
        "service": "quarky_ai",
        "version": VERSION,
        "channel": CHANNEL,
    }
    try:
        from MAIINNN.orchestrator import Orchestrator
        orch = Orchestrator()
        health_data = orch.get_health()
        if health_data:
            basic.update(health_data)
    except Exception:
        pass
    return basic


# ─── Memory ──────────────────────────────────────────────────

@router.get("/memory/stats")
async def memory_stats() -> dict[str, Any]:
    from MAIINNN.Memory.manager import stats
    return await asyncio.to_thread(stats)


@router.get("/memory/search")
async def memory_search(q: str = Query(..., min_length=1)) -> dict[str, Any]:
    from MAIINNN.Memory.manager import recall

    results = await asyncio.to_thread(recall, q.split(), 5)
    return {
        "query": q,
        "total": results.total,
        "permanent": [str(x) for x in results.permanent],
        "priority": [str(x) for x in results.priority],
        "flexible": [str(x) for x in results.flexible],
        "temporary": [str(x) for x in results.temporary],
    }


@router.delete("/memory/{layer}/{entry_id}")
async def memory_forget(layer: str, entry_id: str) -> dict[str, Any]:
    from MAIINNN.Memory import manager as mm

    forget_fns = {
        "temporary": mm.forget_temporary,
        "flexible": mm.forget_flexible,
        "priority": mm.forget_priority,
    }

    if layer == "permanent":
        result = await asyncio.to_thread(
            mm.forget_permanent, entry_id, True
        )
    elif layer in forget_fns:
        result = await asyncio.to_thread(forget_fns[layer], entry_id)
    else:
        raise HTTPException(400, f"Unknown layer: {layer}")

    return {"success": result.success, "message": result.message}


@router.post("/memory/permanent")
async def memory_store_permanent(req: MemoryStoreRequest) -> dict[str, Any]:
    from MAIINNN.Memory.manager import store_permanent

    result = await asyncio.to_thread(
        store_permanent, req.text, req.tags or ["api-saved"], "api"
    )
    return {"success": result.success, "message": result.message, "id": result.data}


# ─── Actions ─────────────────────────────────────────────────

@router.get("/actions/recent")
async def actions_recent(count: int = Query(20, ge=1, le=100)) -> list[dict]:
    from MAIINNN.Functions.action.action_logger import get_recent
    return await asyncio.to_thread(get_recent, count)


@router.get("/actions/stats")
async def actions_stats() -> dict[str, Any]:
    from MAIINNN.Functions.action.action_logger import get_stats
    return await asyncio.to_thread(get_stats)


@router.post("/actions/undo")
async def actions_undo() -> dict[str, Any]:
    from MAIINNN.Functions.action.undo_manager import undo_last
    result = await asyncio.to_thread(undo_last)
    return {"success": result.success, "message": result.message}


# ─── System ──────────────────────────────────────────────────

@router.get("/system/status")
async def system_status() -> dict[str, Any]:
    """Full system dashboard."""
    status: dict[str, Any] = {"timestamp": time.time()}

    # Memory
    try:
        from MAIINNN.Memory.manager import stats
        status["memory"] = await asyncio.to_thread(stats)
    except Exception:
        status["memory"] = "unavailable"

    # Actions
    try:
        from MAIINNN.Functions.action.action_logger import get_stats
        status["actions"] = await asyncio.to_thread(get_stats)
    except Exception:
        status["actions"] = "unavailable"

    # Session
    try:
        from MAIINNN.session import get_session
        status["session"] = get_session().get_stats()
    except Exception:
        status["session"] = "unavailable"

    return status


@router.get("/system/config")
async def system_config() -> dict[str, Any]:
    from AppStudio.Config import (
        FAST_MODE_THRESHOLD, DEEP_MODE_THRESHOLD,
        WORKER_POOL, MEMORY, ACTION, LOG, FEATURES,
    )
    return {
        "fast_threshold": FAST_MODE_THRESHOLD,
        "deep_threshold": DEEP_MODE_THRESHOLD,
        "max_workers": WORKER_POOL["default_max_workers"],
        "decay_interval": MEMORY["decay_interval_seconds"],
        "code_timeout": ACTION["code_runner_timeout"],
        "log_level": LOG["log_level"],
        "features": dict(FEATURES),
    }


@router.post("/system/app")
async def system_register_app(req: AppRegisterRequest) -> dict[str, str]:
    from MAIINNN.Functions.action.app_discovery import add_custom_app
    await asyncio.to_thread(add_custom_app, req.name, req.path)
    return {"message": f"Registered '{req.name}' → {req.path}"}


# ─── Integrations ────────────────────────────────────────────

@router.get("/integrations/status")
async def integrations_status() -> dict[str, Any]:
    """Connected providers and capabilities."""
    try:
        from MAIINNN.orchestrator import get_orchestrator
        integ = get_orchestrator().integrations
        if integ is None:
            return {"connected": False, "providers": []}
        providers = integ.connected_providers()
        return {"connected": bool(providers), "providers": providers}
    except Exception:
        return {"connected": False, "providers": []}


@router.get("/integrations/emails")
async def integrations_emails(
    max_results: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Fetch recent emails from all connected providers."""
    from MAIINNN.orchestrator import get_orchestrator
    integ = get_orchestrator().integrations
    if integ is None:
        raise HTTPException(503, "Integrations not available")
    emails = await asyncio.to_thread(integ.emails, max_results)
    return {
        "count": len(emails),
        "emails": [
            {"id": e.id, "subject": e.subject, "sender": e.sender,
             "snippet": e.snippet, "date": e.date, "provider": e.provider}
            for e in emails
        ],
    }


@router.get("/integrations/events")
async def integrations_events(
    max_results: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Fetch upcoming calendar events from all connected providers."""
    from MAIINNN.orchestrator import get_orchestrator
    integ = get_orchestrator().integrations
    if integ is None:
        raise HTTPException(503, "Integrations not available")
    events = await asyncio.to_thread(integ.events, max_results)
    return {
        "count": len(events),
        "events": [
            {"id": ev.id, "summary": ev.summary, "start": ev.start,
             "end": ev.end, "location": ev.location, "provider": ev.provider}
            for ev in events
        ],
    }
