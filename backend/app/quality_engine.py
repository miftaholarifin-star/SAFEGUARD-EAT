"""Deterministic quality-gate rules for the reference implementation.

Default values reproduce the technical draft as configurable examples. They
are not universal food-safety limits and must be validated for each food type,
process, regulation, and operating context before real use.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Sequence


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    distribution_max_temperature_c: float = 8.0
    max_delivery_delay_minutes: float = 30.0
    min_nutrition_compliance_percent: float = 90.0

    def __post_init__(self) -> None:
        if not -50 <= self.distribution_max_temperature_c <= 100:
            raise ValueError("Ambang suhu berada di luar rentang konfigurasi yang wajar")
        if self.max_delivery_delay_minutes < 0:
            raise ValueError("Ambang keterlambatan tidak boleh negatif")
        if not 0 <= self.min_nutrition_compliance_percent <= 100:
            raise ValueError("Ambang pemenuhan gizi harus berada pada 0 sampai 100 persen")


@dataclass(frozen=True, slots=True)
class QualityInput:
    temperatures_c: Sequence[float]
    nutrition_compliance_percent: float | None
    delivery_delay_minutes: float | None
    documents_complete: bool | None


def evaluate_quality(
    data: QualityInput,
    policy: QualityPolicy | None = None,
) -> dict[str, object]:
    policy = policy or QualityPolicy()
    temperatures = [float(value) for value in data.temperatures_c]
    if any(value < -80 or value > 150 for value in temperatures):
        raise ValueError("Pembacaan suhu berada di luar rentang sensor yang diterima")
    if data.nutrition_compliance_percent is not None and not (
        0 <= data.nutrition_compliance_percent <= 200
    ):
        raise ValueError("Persentase pemenuhan gizi harus berada pada 0 sampai 200")

    checks: dict[str, bool | None] = {
        "temperature": (
            None
            if not temperatures
            else max(temperatures) <= policy.distribution_max_temperature_c
        ),
        "nutrition": (
            None
            if data.nutrition_compliance_percent is None
            else data.nutrition_compliance_percent
            >= policy.min_nutrition_compliance_percent
        ),
        "delivery": (
            None
            if data.delivery_delay_minutes is None
            else data.delivery_delay_minutes < policy.max_delivery_delay_minutes
        ),
        "documents": data.documents_complete,
    }

    violations: list[str] = []
    missing: list[str] = []
    labels = {
        "temperature": "data suhu distribusi",
        "nutrition": "verifikasi pemenuhan gizi",
        "delivery": "data ketepatan pengiriman",
        "documents": "kelengkapan dokumen",
    }
    for name, result in checks.items():
        if result is False:
            violations.append(labels[name])
        elif result is None:
            missing.append(labels[name])

    if missing:
        status = "PENDING_DATA"
        payment_recommendation = "HOLD_PENDING_VERIFICATION"
    elif violations:
        status = "FAILED"
        payment_recommendation = "HOLD_FOR_MANUAL_REVIEW"
    else:
        status = "PASSED"
        payment_recommendation = "ELIGIBLE_FOR_AUTHORIZED_REVIEW"

    temperature_summary: dict[str, float | int | None] = {
        "reading_count": len(temperatures),
        "minimum_c": min(temperatures) if temperatures else None,
        "maximum_c": max(temperatures) if temperatures else None,
        "mean_c": round(fmean(temperatures), 4) if temperatures else None,
    }

    return {
        "status": status,
        "checks": checks,
        "violations": violations,
        "missing_data": missing,
        "temperature_summary": temperature_summary,
        "nutrition_compliance_percent": data.nutrition_compliance_percent,
        "delivery_delay_minutes": (
            round(data.delivery_delay_minutes, 4)
            if data.delivery_delay_minutes is not None
            else None
        ),
        "policy": {
            "distribution_max_temperature_c": policy.distribution_max_temperature_c,
            "max_delivery_delay_minutes_exclusive": policy.max_delivery_delay_minutes,
            "min_nutrition_compliance_percent": policy.min_nutrition_compliance_percent,
            "classification": "draft_illustrative_configuration",
        },
        "payment_recommendation": payment_recommendation,
        "disclaimer": (
            "Hasil adalah dukungan keputusan. Sistem tidak memindahkan dana, "
            "menggantikan inspeksi, atau menetapkan keamanan pangan secara final."
        ),
    }
