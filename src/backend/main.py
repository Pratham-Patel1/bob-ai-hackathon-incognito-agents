"""SupplyChainOS — FastAPI application factory."""
from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import engine
from backend.models import (  # noqa: F401 — ensure all models are imported for metadata
    Carrier, Route, Fleet, Shipment, Disruption,
    ShipmentDisruption, TemperatureLog, Recommendation, DecisionAudit,
)
from backend.database import Base
from backend.routers.health import router as health_router
from backend.routers import (
    shipments_router,
    disruptions_router,
    fleet_router,
    simulations_router,
    recommendations_router,
    audit_router,
    carriers_router,
    routes_router,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create tables and seed data on startup."""
    logger.info("Starting SupplyChainOS (env=%s)", settings.app_env)

    # Create all tables (idempotent — CREATE TABLE IF NOT EXISTS equivalent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created.")

    # Seed synthetic data in development
    if settings.app_env in ("development", "demo"):
        from backend.database import AsyncSessionLocal
        from backend.data.seed import run_seed
        async with AsyncSessionLocal() as session:
            try:
                await run_seed(session)
                await session.commit()
                logger.info("Seed data committed.")
            except Exception as exc:
                await session.rollback()
                logger.error("Seed failed: %s", exc, exc_info=True)

    yield

    # Graceful shutdown
    await engine.dispose()
    logger.info("Database engine disposed.")


# ── Application ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="SupplyChainOS",
        description="AI-Powered Supply Chain Resilience & Digital Twin Control Tower",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handlers ─────────────────────────────────────────────
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    PREFIX = "/api/v1"
    app.include_router(health_router, prefix=PREFIX)
    app.include_router(shipments_router, prefix=PREFIX)
    app.include_router(disruptions_router, prefix=PREFIX)
    app.include_router(fleet_router, prefix=PREFIX)
    app.include_router(simulations_router, prefix=PREFIX)
    app.include_router(recommendations_router, prefix=PREFIX)
    app.include_router(audit_router, prefix=PREFIX)
    app.include_router(carriers_router, prefix=PREFIX)
    app.include_router(routes_router, prefix=PREFIX)

    @app.get("/")
    async def root() -> dict:
        return {
            "service": "SupplyChainOS",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()
