"""Hash-chained audit records used as a local integrity reference layer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


GENESIS_HASH = "0" * 64


def canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_record_hash(
    *,
    previous_hash: str,
    sequence_no: int,
    record_type: str,
    payload: Mapping[str, object],
    occurred_at: str,
) -> str:
    material = "|".join(
        (
            previous_hash,
            str(sequence_no),
            record_type,
            canonical_json(payload),
            occurred_at,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    sequence_no: int
    record_type: str
    payload: Mapping[str, object]
    occurred_at: str
    previous_hash: str
    record_hash: str


def verify_chain(records: Sequence[LedgerRecord]) -> dict[str, object]:
    expected_previous = GENESIS_HASH
    for index, record in enumerate(records, start=1):
        expected_hash = compute_record_hash(
            previous_hash=expected_previous,
            sequence_no=index,
            record_type=record.record_type,
            payload=record.payload,
            occurred_at=record.occurred_at,
        )
        if record.sequence_no != index:
            return {"valid": False, "failed_sequence": index, "reason": "sequence_mismatch"}
        if record.previous_hash != expected_previous:
            return {"valid": False, "failed_sequence": index, "reason": "previous_hash_mismatch"}
        if record.record_hash != expected_hash:
            return {"valid": False, "failed_sequence": index, "reason": "record_hash_mismatch"}
        expected_previous = record.record_hash
    return {
        "valid": True,
        "record_count": len(records),
        "head_hash": expected_previous,
        "implementation": "local_sha256_hash_chain",
    }
