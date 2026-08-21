from __future__ import annotations

import unittest

from backend.app.quality_engine import QualityInput, QualityPolicy, evaluate_quality


class QualityEngineTests(unittest.TestCase):
    def test_passes_complete_compliant_batch(self) -> None:
        result = evaluate_quality(
            QualityInput(
                temperatures_c=[4.0, 5.5, 7.9],
                nutrition_compliance_percent=96,
                delivery_delay_minutes=12,
                documents_complete=True,
            )
        )
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["payment_recommendation"], "ELIGIBLE_FOR_AUTHORIZED_REVIEW")
        self.assertEqual(result["violations"], [])

    def test_fails_high_temperature(self) -> None:
        result = evaluate_quality(
            QualityInput(
                temperatures_c=[6.0, 8.1],
                nutrition_compliance_percent=95,
                delivery_delay_minutes=10,
                documents_complete=True,
            )
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(result["checks"]["temperature"])

    def test_requires_all_evidence(self) -> None:
        result = evaluate_quality(
            QualityInput(
                temperatures_c=[],
                nutrition_compliance_percent=None,
                delivery_delay_minutes=None,
                documents_complete=False,
            )
        )
        self.assertEqual(result["status"], "PENDING_DATA")
        self.assertIn("data suhu distribusi", result["missing_data"])

    def test_delay_threshold_is_exclusive(self) -> None:
        result = evaluate_quality(
            QualityInput(
                temperatures_c=[5],
                nutrition_compliance_percent=90,
                delivery_delay_minutes=30,
                documents_complete=True,
            )
        )
        self.assertFalse(result["checks"]["delivery"])

    def test_rejects_invalid_policy(self) -> None:
        with self.assertRaisesRegex(ValueError, "pemenuhan gizi"):
            QualityPolicy(min_nutrition_compliance_percent=120)


if __name__ == "__main__":
    unittest.main()
