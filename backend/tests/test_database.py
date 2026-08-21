from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app.database import SafeguardStore
from backend.app.quality_engine import QualityPolicy


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SafeguardStore(Path(self.temp_dir.name) / "test.db")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_complete_batch(self) -> dict[str, object]:
        batch = self.store.create_batch(
            batch_code="SGE-TEST-001",
            supplier_name="Penyedia Contoh",
            food_description="Paket pangan contoh",
            production_date="2026-01-01",
            documents_complete=True,
        )
        self.store.record_iot(
            "SGE-TEST-001",
            observed_at="2026-01-01T08:00:00+00:00",
            temperature_c=6.5,
            humidity_percent=70,
            location_label="Hub agregat",
            device_id="SIM-001",
        )
        self.store.record_nutrition(
            "SGE-TEST-001",
            compliance_percent=95,
            lab_reference="LAB-DEMO-001",
            verified_by="Verifier Contoh",
            verified_at="2026-01-01T09:00:00+00:00",
        )
        self.store.record_delivery(
            "SGE-TEST-001",
            scheduled_at="2026-01-01T10:00:00+00:00",
            delivered_at="2026-01-01T10:15:00+00:00",
            received_by="Penerima Contoh",
        )
        return batch

    def test_end_to_end_trace_is_valid(self) -> None:
        batch = self.create_complete_batch()
        evaluation = self.store.evaluate_batch("SGE-TEST-001", QualityPolicy())
        trace = self.store.get_trace("SGE-TEST-001")
        public = self.store.get_public_trace(str(batch["qr_token"]))
        self.assertEqual(evaluation["status"], "PASSED")
        self.assertTrue(trace["integrity"]["valid"])
        self.assertEqual(trace["integrity"]["record_count"], 5)
        self.assertEqual(public["batch_code"], "SGE-TEST-001")
        self.assertEqual(public["status"], "PASSED")

    def test_duplicate_batch_is_rejected(self) -> None:
        self.create_complete_batch()
        with self.assertRaisesRegex(ValueError, "sudah digunakan"):
            self.store.create_batch(
                batch_code="SGE-TEST-001",
                supplier_name="Penyedia Lain",
                food_description="Paket lain",
                production_date="2026-01-02",
                documents_complete=False,
            )

    def test_missing_batch_is_rejected(self) -> None:
        with self.assertRaisesRegex(KeyError, "tidak ditemukan"):
            self.store.get_trace("SGE-NOT-FOUND")


if __name__ == "__main__":
    unittest.main()
