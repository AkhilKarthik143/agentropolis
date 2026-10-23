from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = PROJECT_ROOT / "backend" / ".data"


def _data_dir() -> Path:
    configured = Path(os.getenv("AGENTROPOLIS_DATA_DIR", str(DEFAULT_DATA_DIR)))
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings owned by the standalone application."""

    app_name: str = "Agentropolis API"
    host: str = os.getenv("AGENTROPOLIS_HOST", "127.0.0.1")
    port: int = int(os.getenv("AGENTROPOLIS_PORT", "8001"))
    data_dir: Path = _data_dir()
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
