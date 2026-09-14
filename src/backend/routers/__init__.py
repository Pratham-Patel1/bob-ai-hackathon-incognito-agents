"""
SupplyChainOS API Routers package.
Exports all domain routers for inclusion in the main FastAPI application.
"""
from __future__ import annotations

from backend.routers.health import router as health_router
from backend.routers.shipments import router as shipments_router
from backend.routers.disruptions import router as disruptions_router
from backend.routers.fleet import router as fleet_router
from backend.routers.simulations import router as simulations_router
from backend.routers.recommendations import router as recommendations_router
from backend.routers.carriers import router as carriers_router
from backend.routers.routes import router as routes_router
from backend.routers.audit import router as audit_router

__all__ = [
    "health_router",
    "shipments_router",
    "disruptions_router",
    "fleet_router",
    "simulations_router",
    "recommendations_router",
    "carriers_router",
    "routes_router",
    "audit_router",
]
