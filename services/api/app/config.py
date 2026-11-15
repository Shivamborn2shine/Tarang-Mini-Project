"""Runtime configuration for TARANG API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "TARANG_DATABASE_URL",
        f"sqlite:///{(Path(__file__).resolve().parents[1] / 'tarang_local.db').as_posix()}",
    )
    upload_dir: Path = Path(
        os.getenv("TARANG_UPLOAD_DIR", str(Path(__file__).resolve().parents[1] / "uploads"))
    )
    cors_origins: tuple[str, ...] = tuple(
        os.getenv("TARANG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    )


settings = Settings()
