"""
SupplyChainOS — Application Settings
All configuration is loaded from environment variables.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://supplychainOS:password@localhost:5432/supplychainOS"
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_port: int = 8000
    app_env: str = "development"
    log_level: str = "INFO"

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Business rules ────────────────────────────────────────────────────────
    approval_threshold_usd: float = 50_000.0
    sla_buffer_hours: float = 4.0
    daily_holding_cost_rate: float = 0.002
    default_sla_penalty_usd: float = 5_000.0

    # ── ML ────────────────────────────────────────────────────────────────────
    ml_model_path: str = "../ml/artifacts/risk_model.joblib"
    ml_deterministic_weight: float = 0.6
    ml_predictive_weight: float = 0.4

    # ── watsonx.ai (Phase 2) ──────────────────────────────────────────────────
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"

    # ── Notifications (Phase 2) ───────────────────────────────────────────────
    slack_webhook_url: str = ""


settings = Settings()
