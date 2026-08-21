"""SQLite persistence and traceability services."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from .integrity import GENESIS_HASH, LedgerRecord, canonical_json, compute_record_hash, verify_chain
from .quality_engine import QualityInput, QualityPolicy, evaluate_quality


BATCH_CODE_PATTERN = re.compile(r"^[A-Z0-9-]{3,64}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SafeguardStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS food_batches (
                    batch_code TEXT PRIMARY KEY,
                    supplier_name TEXT NOT NULL,
                    food_description TEXT NOT NULL,
                    production_date TEXT NOT NULL,
                    documents_complete INTEGER NOT NULL,
                    qr_token TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS iot_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_code TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    humidity_percent REAL,
                    location_label TEXT,
                    device_id TEXT NOT NULL,
                    FOREIGN KEY(batch_code) REFERENCES food_batches(batch_code)
                );

                CREATE TABLE IF NOT EXISTS nutrition_data (
                    batch_code TEXT PRIMARY KEY,
                    compliance_percent REAL NOT NULL,
                    lab_reference TEXT NOT NULL,
                    verified_by TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    FOREIGN KEY(batch_code) REFERENCES food_batches(batch_code)
                );

                CREATE TABLE IF NOT EXISTS deliveries (
                    batch_code TEXT PRIMARY KEY,
                    scheduled_at TEXT NOT NULL,
                    delivered_at TEXT NOT NULL,
                    received_by TEXT NOT NULL,
                    FOREIGN KEY(batch_code) REFERENCES food_batches(batch_code)
                );

                CREATE TABLE IF NOT EXISTS quality_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    FOREIGN KEY(batch_code) REFERENCES food_batches(batch_code)
                );

                CREATE TABLE IF NOT EXISTS ledger_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_code TEXT NOT NULL,
                    sequence_no INTEGER NOT NULL,
                    record_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    UNIQUE(batch_code, sequence_no),
                    FOREIGN KEY(batch_code) REFERENCES food_batches(batch_code)
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_code TEXT,
                    action TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _normalize_code(batch_code: str) -> str:
        code = batch_code.strip().upper()
        if not BATCH_CODE_PATTERN.fullmatch(code):
            raise ValueError("Kode batch hanya boleh memuat huruf, angka, dan tanda hubung")
        return code

    @staticmethod
    def _require_batch(connection: sqlite3.Connection, batch_code: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM food_batches WHERE batch_code = ?", (batch_code,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Batch {batch_code} tidak ditemukan")
        return row

    def _append_ledger(
        self,
        connection: sqlite3.Connection,
        batch_code: str,
        record_type: str,
        payload: Mapping[str, object],
        occurred_at: str | None = None,
    ) -> str:
        occurred_at = occurred_at or utc_now()
        latest = connection.execute(
            """
            SELECT sequence_no, record_hash
            FROM ledger_records
            WHERE batch_code = ?
            ORDER BY sequence_no DESC
            LIMIT 1
            """,
            (batch_code,),
        ).fetchone()
        sequence_no = 1 if latest is None else int(latest["sequence_no"]) + 1
        previous_hash = GENESIS_HASH if latest is None else str(latest["record_hash"])
        record_hash = compute_record_hash(
            previous_hash=previous_hash,
            sequence_no=sequence_no,
            record_type=record_type,
            payload=payload,
            occurred_at=occurred_at,
        )
        connection.execute(
            """
            INSERT INTO ledger_records (
                batch_code, sequence_no, record_type, payload_json,
                occurred_at, previous_hash, record_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_code,
                sequence_no,
                record_type,
                canonical_json(payload),
                occurred_at,
                previous_hash,
                record_hash,
            ),
        )
        return record_hash

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        action: str,
        detail: Mapping[str, object],
        batch_code: str | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_logs (batch_code, action, detail_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (batch_code, action, canonical_json(detail), utc_now()),
        )

    def create_batch(
        self,
        *,
        supplier_name: str,
        food_description: str,
        production_date: str,
        documents_complete: bool,
        batch_code: str | None = None,
    ) -> dict[str, object]:
        generated = batch_code or f"SGE-{production_date.replace('-', '')}-{uuid4().hex[:8].upper()}"
        code = self._normalize_code(generated)
        qr_token = uuid4().hex
        created_at = utc_now()
        payload = {
            "batch_code": code,
            "supplier_name": supplier_name.strip(),
            "food_description": food_description.strip(),
            "production_date": production_date,
            "documents_complete": bool(documents_complete),
            "qr_token": qr_token,
        }
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO food_batches (
                        batch_code, supplier_name, food_description, production_date,
                        documents_complete, qr_token, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        payload["supplier_name"],
                        payload["food_description"],
                        production_date,
                        int(documents_complete),
                        qr_token,
                        "REGISTERED",
                        created_at,
                    ),
                )
                head_hash = self._append_ledger(connection, code, "BATCH_REGISTERED", payload)
                self._audit(connection, "BATCH_REGISTERED", payload, code)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Kode batch {code} sudah digunakan") from exc
        return {**payload, "status": "REGISTERED", "created_at": created_at, "head_hash": head_hash}

    def record_iot(
        self,
        batch_code: str,
        *,
        observed_at: str,
        temperature_c: float,
        humidity_percent: float | None,
        location_label: str | None,
        device_id: str,
    ) -> dict[str, object]:
        code = self._normalize_code(batch_code)
        payload = {
            "observed_at": observed_at,
            "temperature_c": float(temperature_c),
            "humidity_percent": humidity_percent,
            "location_label": location_label,
            "device_id": device_id,
        }
        with self._connect() as connection:
            self._require_batch(connection, code)
            cursor = connection.execute(
                """
                INSERT INTO iot_logs (
                    batch_code, observed_at, temperature_c, humidity_percent,
                    location_label, device_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    code,
                    observed_at,
                    temperature_c,
                    humidity_percent,
                    location_label,
                    device_id,
                ),
            )
            head_hash = self._append_ledger(connection, code, "IOT_RECORDED", payload)
            self._audit(connection, "IOT_RECORDED", {"iot_log_id": cursor.lastrowid}, code)
        return {"iot_log_id": cursor.lastrowid, "batch_code": code, **payload, "head_hash": head_hash}

    def record_nutrition(
        self,
        batch_code: str,
        *,
        compliance_percent: float,
        lab_reference: str,
        verified_by: str,
        verified_at: str,
    ) -> dict[str, object]:
        code = self._normalize_code(batch_code)
        payload = {
            "compliance_percent": float(compliance_percent),
            "lab_reference": lab_reference,
            "verified_by": verified_by,
            "verified_at": verified_at,
        }
        with self._connect() as connection:
            self._require_batch(connection, code)
            connection.execute(
                """
                INSERT INTO nutrition_data (
                    batch_code, compliance_percent, lab_reference, verified_by, verified_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(batch_code) DO UPDATE SET
                    compliance_percent = excluded.compliance_percent,
                    lab_reference = excluded.lab_reference,
                    verified_by = excluded.verified_by,
                    verified_at = excluded.verified_at
                """,
                (code, compliance_percent, lab_reference, verified_by, verified_at),
            )
            head_hash = self._append_ledger(connection, code, "NUTRITION_VERIFIED", payload)
            self._audit(connection, "NUTRITION_VERIFIED", payload, code)
        return {"batch_code": code, **payload, "head_hash": head_hash}

    def record_delivery(
        self,
        batch_code: str,
        *,
        scheduled_at: str,
        delivered_at: str,
        received_by: str,
    ) -> dict[str, object]:
        code = self._normalize_code(batch_code)
        payload = {
            "scheduled_at": scheduled_at,
            "delivered_at": delivered_at,
            "received_by": received_by,
        }
        with self._connect() as connection:
            self._require_batch(connection, code)
            connection.execute(
                """
                INSERT INTO deliveries (batch_code, scheduled_at, delivered_at, received_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(batch_code) DO UPDATE SET
                    scheduled_at = excluded.scheduled_at,
                    delivered_at = excluded.delivered_at,
                    received_by = excluded.received_by
                """,
                (code, scheduled_at, delivered_at, received_by),
            )
            head_hash = self._append_ledger(connection, code, "DELIVERY_RECEIVED", payload)
            self._audit(connection, "DELIVERY_RECEIVED", payload, code)
        return {"batch_code": code, **payload, "head_hash": head_hash}

    def evaluate_batch(self, batch_code: str, policy: QualityPolicy) -> dict[str, object]:
        code = self._normalize_code(batch_code)
        with self._connect() as connection:
            batch = self._require_batch(connection, code)
            temperatures = [
                float(row["temperature_c"])
                for row in connection.execute(
                    "SELECT temperature_c FROM iot_logs WHERE batch_code = ? ORDER BY observed_at",
                    (code,),
                ).fetchall()
            ]
            nutrition = connection.execute(
                "SELECT * FROM nutrition_data WHERE batch_code = ?", (code,)
            ).fetchone()
            delivery = connection.execute(
                "SELECT * FROM deliveries WHERE batch_code = ?", (code,)
            ).fetchone()
            delay_minutes = None
            if delivery is not None:
                scheduled = datetime.fromisoformat(str(delivery["scheduled_at"]))
                delivered = datetime.fromisoformat(str(delivery["delivered_at"]))
                delay_minutes = (delivered - scheduled).total_seconds() / 60.0

            result = evaluate_quality(
                QualityInput(
                    temperatures_c=temperatures,
                    nutrition_compliance_percent=(
                        None if nutrition is None else float(nutrition["compliance_percent"])
                    ),
                    delivery_delay_minutes=delay_minutes,
                    documents_complete=bool(batch["documents_complete"]),
                ),
                policy,
            )
            evaluated_at = utc_now()
            connection.execute(
                """
                INSERT INTO quality_evaluations (
                    batch_code, status, result_json, evaluated_at
                ) VALUES (?, ?, ?, ?)
                """,
                (code, result["status"], json.dumps(result, ensure_ascii=False), evaluated_at),
            )
            connection.execute(
                "UPDATE food_batches SET status = ? WHERE batch_code = ?",
                (result["status"], code),
            )
            ledger_payload = {
                "status": result["status"],
                "checks": result["checks"],
                "payment_recommendation": result["payment_recommendation"],
            }
            head_hash = self._append_ledger(
                connection, code, "QUALITY_EVALUATED", ledger_payload, evaluated_at
            )
            self._audit(connection, "QUALITY_EVALUATED", ledger_payload, code)
        return {"batch_code": code, "evaluated_at": evaluated_at, **result, "head_hash": head_hash}

    def get_trace(self, batch_code: str) -> dict[str, object]:
        code = self._normalize_code(batch_code)
        with self._connect() as connection:
            batch = self._require_batch(connection, code)
            sensors = connection.execute(
                "SELECT * FROM iot_logs WHERE batch_code = ? ORDER BY observed_at", (code,)
            ).fetchall()
            nutrition = connection.execute(
                "SELECT * FROM nutrition_data WHERE batch_code = ?", (code,)
            ).fetchone()
            delivery = connection.execute(
                "SELECT * FROM deliveries WHERE batch_code = ?", (code,)
            ).fetchone()
            evaluation = connection.execute(
                """
                SELECT result_json, evaluated_at FROM quality_evaluations
                WHERE batch_code = ? ORDER BY id DESC LIMIT 1
                """,
                (code,),
            ).fetchone()
            ledger_rows = connection.execute(
                "SELECT * FROM ledger_records WHERE batch_code = ? ORDER BY sequence_no", (code,)
            ).fetchall()

        ledger = [
            LedgerRecord(
                sequence_no=int(row["sequence_no"]),
                record_type=str(row["record_type"]),
                payload=json.loads(str(row["payload_json"])),
                occurred_at=str(row["occurred_at"]),
                previous_hash=str(row["previous_hash"]),
                record_hash=str(row["record_hash"]),
            )
            for row in ledger_rows
        ]
        return {
            "batch": {
                "batch_code": batch["batch_code"],
                "supplier_name": batch["supplier_name"],
                "food_description": batch["food_description"],
                "production_date": batch["production_date"],
                "documents_complete": bool(batch["documents_complete"]),
                "qr_token": batch["qr_token"],
                "status": batch["status"],
                "created_at": batch["created_at"],
            },
            "iot_logs": [dict(row) for row in sensors],
            "nutrition": None if nutrition is None else dict(nutrition),
            "delivery": None if delivery is None else dict(delivery),
            "latest_evaluation": (
                None
                if evaluation is None
                else {
                    **json.loads(str(evaluation["result_json"])),
                    "evaluated_at": evaluation["evaluated_at"],
                }
            ),
            "integrity": verify_chain(ledger),
            "ledger": [
                {
                    "sequence_no": item.sequence_no,
                    "record_type": item.record_type,
                    "occurred_at": item.occurred_at,
                    "previous_hash": item.previous_hash,
                    "record_hash": item.record_hash,
                }
                for item in ledger
            ],
            "blockchain_note": (
                "Jejak ini memakai hash-chain SHA-256 lokal. Anchoring ke jaringan "
                "blockchain eksternal belum dilakukan oleh implementasi referensi."
            ),
        }

    def get_public_trace(self, qr_token: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT batch_code FROM food_batches WHERE qr_token = ?", (qr_token,)
            ).fetchone()
        if row is None:
            raise KeyError("QR token tidak ditemukan")
        trace = self.get_trace(str(row["batch_code"]))
        batch = trace["batch"]
        return {
            "batch_code": batch["batch_code"],
            "supplier_name": batch["supplier_name"],
            "food_description": batch["food_description"],
            "production_date": batch["production_date"],
            "status": batch["status"],
            "sensor_reading_count": len(trace["iot_logs"]),
            "nutrition_compliance_percent": (
                None if trace["nutrition"] is None else trace["nutrition"]["compliance_percent"]
            ),
            "latest_evaluation": trace["latest_evaluation"],
            "integrity": trace["integrity"],
            "notice": "Data demonstrasi. Verifikasi fisik dan dokumen tetap diperlukan.",
        }
