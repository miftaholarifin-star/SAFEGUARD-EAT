from __future__ import annotations

import unittest

from backend.app.integrity import GENESIS_HASH, LedgerRecord, compute_record_hash, verify_chain


def build_record(previous: str, sequence: int, payload: dict[str, object]) -> LedgerRecord:
    occurred_at = f"2026-01-0{sequence}T00:00:00+00:00"
    record_type = "TEST_EVENT"
    digest = compute_record_hash(
        previous_hash=previous,
        sequence_no=sequence,
        record_type=record_type,
        payload=payload,
        occurred_at=occurred_at,
    )
    return LedgerRecord(sequence, record_type, payload, occurred_at, previous, digest)


class IntegrityTests(unittest.TestCase):
    def test_valid_chain(self) -> None:
        first = build_record(GENESIS_HASH, 1, {"value": 1})
        second = build_record(first.record_hash, 2, {"value": 2})
        result = verify_chain([first, second])
        self.assertTrue(result["valid"])
        self.assertEqual(result["head_hash"], second.record_hash)

    def test_detects_payload_tampering(self) -> None:
        original = build_record(GENESIS_HASH, 1, {"value": 1})
        tampered = LedgerRecord(
            original.sequence_no,
            original.record_type,
            {"value": 999},
            original.occurred_at,
            original.previous_hash,
            original.record_hash,
        )
        result = verify_chain([tampered])
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "record_hash_mismatch")

    def test_hash_is_deterministic_for_key_order(self) -> None:
        first = compute_record_hash(
            previous_hash=GENESIS_HASH,
            sequence_no=1,
            record_type="EVENT",
            payload={"a": 1, "b": 2},
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        second = compute_record_hash(
            previous_hash=GENESIS_HASH,
            sequence_no=1,
            record_type="EVENT",
            payload={"b": 2, "a": 1},
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
