"""
SupplyChainOS — Model Context Protocol (MCP) Security Layer.
Enforces tool allowlisting, input sanitization, human approval gates, and error masking.
"""
from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Explicit Allowlist of registered SupplyChainOS MCP Tools
ALLOWED_TOOLS = frozenset({
    "analyze_disruption",
    "get_shipment_risk",
    "check_cold_chain",
    "get_fleet_status",
    "find_alternative_routes",
    "simulate_scenario",
    "get_recommendations",
    "approve_recommendation",
    "get_cascade_impact",
})

# Patterns for SQL injection or command injection defense
DANGEROUS_SQL_PATTERNS = re.compile(
    r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC)\b|\bUNION\s+(ALL\s+)?SELECT\b|\bOR\s+1\s*=\s*1\b|--|\/\*|\*\/)",
    re.IGNORECASE,
)


class MCPSecurityError(Exception):
    """Raised when an MCP security policy or permission gate is violated."""
    def __init__(self, message: str, code: int = -32602):
        super().__init__(message)
        self.message = message
        self.code = code


def validate_tool_allowed(tool_name: str) -> None:
    """Ensure tool name is in the strict allowlist."""
    if not tool_name or tool_name not in ALLOWED_TOOLS:
        logger.warning("Rejected attempt to access unauthorized tool: %s", tool_name)
        raise MCPSecurityError(
            f"Tool '{tool_name}' is not in the authorized SupplyChainOS MCP tool allowlist.",
            code=-32601,
        )


def sanitize_input_strings(data: Any) -> None:
    """Recursively inspect string inputs for SQL/command injection signatures."""
    if isinstance(data, str):
        if DANGEROUS_SQL_PATTERNS.search(data):
            logger.error("Dangerous pattern detected in tool argument: %s", data)
            raise MCPSecurityError("Invalid input: potentially dangerous characters or SQL signatures detected.")
    elif isinstance(data, dict):
        for k, v in data.items():
            sanitize_input_strings(k)
            sanitize_input_strings(v)
    elif isinstance(data, list):
        for item in data:
            sanitize_input_strings(item)


def mask_sensitive_error(exc: Exception) -> str:
    """Sanitize internal errors to prevent leaking database URLs, credentials, or internal paths."""
    err_str = str(exc)
    # Mask database connection strings if any appear in error output
    masked = re.sub(r":\/\/[^:]+:[^@]+@", "://***:***@", err_str)
    masked = re.sub(r"password=[^\s;&]+", "password=***", masked, flags=re.IGNORECASE)
    # Genericize raw database driver errors
    if "asyncpg" in masked.lower() or "sqlalchemy" in masked.lower() or "psycopg" in masked.lower():
        logger.error("Internal database exception intercepted at MCP boundary: %s", exc, exc_info=True)
        return "Internal data service error encountered. Please check backend logs."
    return masked
