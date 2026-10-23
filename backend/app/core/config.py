from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings owned by the standalone application."""

    app_name: str = "Agentropolis API"
    host: str = os.getenv("AGENTROPOLIS_HOST", "127.0.0.1")
    port: int = int(os.getenv("AGENTROPOLIS_PORT", "8001"))
    data_dir: Path = Path(os.getenv("AGENTROPOLIS_DATA_DIR", str(Path(__file__).resolve().parents[2] / ".data")))
    store: str = os.getenv("AGENTROPOLIS_STORE", "sqlite").lower()
    seed: int = int(os.getenv("AGENTROPOLIS_SEED", "13"))
    llm_mode: str = os.getenv("AGENTROPOLIS_LLM_MODE", "replay")
    frontend_origin: str = os.getenv("AGENTROPOLIS_FRONTEND_ORIGIN", "http://127.0.0.1:5173")

    @property
    def event_database(self) -> Path:
        return self.data_dir / "economy.db"

    @property
    def cors_origins(self) -> list[str]:
        raw = os.getenv("AGENTROPOLIS_CORS_ORIGINS", self.frontend_origin)
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
