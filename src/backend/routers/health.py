"""Health check endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict:
    """Liveness check — confirms the application is running."""
    return {"status": "ok", "service": "SupplyChainOS"}


@router.get("/db")
async def health_db(session: AsyncSession = Depends(get_async_db)) -> dict:
    """DB connectivity check — confirms PostgreSQL is reachable."""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
