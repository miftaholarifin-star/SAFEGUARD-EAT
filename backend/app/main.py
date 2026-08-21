"""FastAPI application for SAFEGUARD EAT."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .database import SafeguardStore
from .models import BatchCreate, DeliveryCreate, HealthResponse, NutritionCreate, TelemetryCreate
from .quality_engine import QualityPolicy


app = FastAPI(
    title="SAFEGUARD EAT API",
    description=(
        "Implementasi referensi traceability batch pangan, quality gate, "
        "telemetri IoT, verifikasi gizi, dan jejak audit berbasis hash."
    ),
    version=__version__,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

store = SafeguardStore(settings.database_path)
policy = QualityPolicy(
    distribution_max_temperature_c=settings.distribution_max_temperature_c,
    max_delivery_delay_minutes=settings.max_delivery_delay_minutes,
    min_nutrition_compliance_percent=settings.min_nutrition_compliance_percent,
)


def _not_found(exc: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc).strip("'"))


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="SAFEGUARD EAT API",
        version=__version__,
        implementation_status="reference_prototype",
    )


@app.get("/api/v1/policy", tags=["quality"])
def get_policy() -> dict[str, object]:
    return {
        "distribution_max_temperature_c": policy.distribution_max_temperature_c,
        "max_delivery_delay_minutes_exclusive": policy.max_delivery_delay_minutes,
        "min_nutrition_compliance_percent": policy.min_nutrition_compliance_percent,
        "classification": "draft_illustrative_configuration",
        "notice": "Ambang harus divalidasi berdasarkan jenis pangan dan regulasi yang berlaku",
    }


@app.post("/api/v1/batches", status_code=status.HTTP_201_CREATED, tags=["batches"])
def create_batch(payload: BatchCreate) -> dict[str, object]:
    try:
        return store.create_batch(
            batch_code=payload.batch_code,
            supplier_name=payload.supplier_name,
            food_description=payload.food_description,
            production_date=payload.production_date.isoformat(),
            documents_complete=payload.documents_complete,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/batches/{batch_code}/iot", tags=["iot"])
def record_iot(batch_code: str, payload: TelemetryCreate) -> dict[str, object]:
    try:
        return store.record_iot(
            batch_code,
            observed_at=payload.observed_at.isoformat(),
            temperature_c=payload.temperature_c,
            humidity_percent=payload.humidity_percent,
            location_label=payload.location_label,
            device_id=payload.device_id,
        )
    except KeyError as exc:
        raise _not_found(exc) from exc


@app.post("/api/v1/batches/{batch_code}/nutrition", tags=["nutrition"])
def record_nutrition(batch_code: str, payload: NutritionCreate) -> dict[str, object]:
    try:
        return store.record_nutrition(
            batch_code,
            compliance_percent=payload.compliance_percent,
            lab_reference=payload.lab_reference,
            verified_by=payload.verified_by,
            verified_at=payload.verified_at.isoformat(),
        )
    except KeyError as exc:
        raise _not_found(exc) from exc


@app.post("/api/v1/batches/{batch_code}/delivery", tags=["delivery"])
def record_delivery(batch_code: str, payload: DeliveryCreate) -> dict[str, object]:
    try:
        return store.record_delivery(
            batch_code,
            scheduled_at=payload.scheduled_at.isoformat(),
            delivered_at=payload.delivered_at.isoformat(),
            received_by=payload.received_by,
        )
    except KeyError as exc:
        raise _not_found(exc) from exc


@app.post("/api/v1/batches/{batch_code}/evaluate", tags=["quality"])
def evaluate_batch(batch_code: str) -> dict[str, object]:
    try:
        return store.evaluate_batch(batch_code, policy)
    except KeyError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/batches/{batch_code}/trace", tags=["traceability"])
def trace_batch(batch_code: str) -> dict[str, object]:
    try:
        return store.get_trace(batch_code)
    except KeyError as exc:
        raise _not_found(exc) from exc


@app.get("/api/v1/qr/{qr_token}", tags=["public-trace"])
def public_trace(qr_token: str) -> dict[str, object]:
    try:
        return store.get_public_trace(qr_token)
    except KeyError as exc:
        raise _not_found(exc) from exc
