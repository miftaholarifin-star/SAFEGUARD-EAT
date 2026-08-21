"""Pydantic request models for the SAFEGUARD EAT API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    implementation_status: str


class BatchCreate(BaseModel):
    batch_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{3,64}$")
    supplier_name: str = Field(min_length=2, max_length=160)
    food_description: str = Field(min_length=2, max_length=240)
    production_date: date
    documents_complete: bool = False


class TelemetryCreate(BaseModel):
    observed_at: datetime
    temperature_c: float = Field(ge=-80, le=150)
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    location_label: str | None = Field(default=None, max_length=160)
    device_id: str = Field(default="SIMULATED-DEVICE", min_length=2, max_length=100)


class NutritionCreate(BaseModel):
    compliance_percent: float = Field(ge=0, le=200)
    lab_reference: str = Field(min_length=2, max_length=160)
    verified_by: str = Field(min_length=2, max_length=160)
    verified_at: datetime


class DeliveryCreate(BaseModel):
    scheduled_at: datetime
    delivered_at: datetime
    received_by: str = Field(min_length=2, max_length=160)

    @model_validator(mode="after")
    def validate_dates(self) -> "DeliveryCreate":
        if self.delivered_at < self.scheduled_at:
            raise ValueError("Waktu penerimaan tidak boleh lebih awal dari jadwal")
        return self
