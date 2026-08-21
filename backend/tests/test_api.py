from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.database import SafeguardStore


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        main.store = SafeguardStore(Path(cls.temp_dir.name) / "api-test.db")
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_health_and_policy_are_transparent(self) -> None:
        health = self.client.get("/health")
        policy = self.client.get("/api/v1/policy")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["version"], "1.0.0")
        self.assertEqual(policy.json()["classification"], "draft_illustrative_configuration")

    def test_complete_batch_workflow(self) -> None:
        code = "SGE-API-001"
        created = self.client.post(
            "/api/v1/batches",
            json={
                "batch_code": code,
                "supplier_name": "Penyedia Sintetis",
                "food_description": "Menu contoh",
                "production_date": date.today().isoformat(),
                "documents_complete": True,
            },
        )
        self.assertEqual(created.status_code, 201)

        telemetry = self.client.post(
            f"/api/v1/batches/{code}/iot",
            json={
                "observed_at": "2026-01-01T08:00:00Z",
                "temperature_c": 7.0,
                "humidity_percent": 68,
                "location_label": "Lokasi agregat",
                "device_id": "SIM-API",
            },
        )
        nutrition = self.client.post(
            f"/api/v1/batches/{code}/nutrition",
            json={
                "compliance_percent": 92,
                "lab_reference": "LAB-SYNTHETIC",
                "verified_by": "Verifier Sintetis",
                "verified_at": "2026-01-01T09:00:00Z",
            },
        )
        delivery = self.client.post(
            f"/api/v1/batches/{code}/delivery",
            json={
                "scheduled_at": "2026-01-01T10:00:00Z",
                "delivered_at": "2026-01-01T10:20:00Z",
                "received_by": "Sekolah Contoh",
            },
        )
        self.assertEqual(telemetry.status_code, 200)
        self.assertEqual(nutrition.status_code, 200)
        self.assertEqual(delivery.status_code, 200)

        evaluation = self.client.post(f"/api/v1/batches/{code}/evaluate")
        trace = self.client.get(f"/api/v1/batches/{code}/trace")
        qr_token = created.json()["qr_token"]
        public = self.client.get(f"/api/v1/qr/{qr_token}")
        self.assertEqual(evaluation.json()["status"], "PASSED")
        self.assertTrue(trace.json()["integrity"]["valid"])
        self.assertEqual(public.json()["status"], "PASSED")

    def test_unknown_batch_returns_404(self) -> None:
        response = self.client.get("/api/v1/batches/SGE-UNKNOWN/trace")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
