"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} harus berupa angka") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    distribution_max_temperature_c: float
    max_delivery_delay_minutes: float
    min_nutrition_compliance_percent: float
    allowed_origins: tuple[str, ...]


def load_settings() -> Settings:
    origins = tuple(
        item.strip()
        for item in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500").split(",")
        if item.strip()
    )
    return Settings(
        database_path=Path(os.getenv("DATABASE_PATH", "safeguard_eat.db")),
        distribution_max_temperature_c=_float_env(
            "DISTRIBUTION_MAX_TEMPERATURE_C", 8.0
        ),
        max_delivery_delay_minutes=_float_env("MAX_DELIVERY_DELAY_MINUTES", 30.0),
        min_nutrition_compliance_percent=_float_env(
            "MIN_NUTRITION_COMPLIANCE_PERCENT", 90.0
        ),
        allowed_origins=origins,
    )


settings = load_settings()
