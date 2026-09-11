import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from app.models.medical_record import MedicalRecord


MEDICAL_RECORD_STORE_SCHEMA_VERSION = 1
DEFAULT_MEDICAL_RECORD_STORE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "medical_records.json"
)


def resolve_medical_record_store_path(
    store_path: str | Path | None = None,
) -> Path:
    if store_path is not None:
        return Path(store_path)

    configured_path = os.getenv("MEDICAL_RECORD_STORE_PATH")

    if configured_path:
        return Path(configured_path)

    return DEFAULT_MEDICAL_RECORD_STORE_PATH


def save_medical_records(
    records: Iterable[MedicalRecord],
    store_path: str | Path | None = None,
) -> Path:
    destination = resolve_medical_record_store_path(store_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": MEDICAL_RECORD_STORE_SCHEMA_VERSION,
        "medical_records": [
            record.model_dump(mode="json")
            for record in records
        ],
    }
    temporary_path: Path | None = None

    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_path, destination)

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return destination


def load_medical_records(
    store_path: str | Path | None = None,
) -> list[MedicalRecord]:
    source = resolve_medical_record_store_path(store_path)

    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("Medical-record store must contain a JSON object.")

    if payload.get("schema_version") != MEDICAL_RECORD_STORE_SCHEMA_VERSION:
        raise ValueError("Medical-record store schema version is unsupported.")

    serialized_records = payload.get("medical_records")

    if not isinstance(serialized_records, list):
        raise ValueError("Medical-record store is missing medical_records.")

    return [
        MedicalRecord.model_validate(record)
        for record in serialized_records
    ]


def load_or_initialize_medical_records(
    default_records: Iterable[MedicalRecord],
    store_path: str | Path | None = None,
) -> list[MedicalRecord]:
    destination = resolve_medical_record_store_path(store_path)

    if destination.exists():
        return load_medical_records(destination)

    initialized_records = [
        record.model_copy(deep=True)
        for record in default_records
    ]
    save_medical_records(initialized_records, destination)
    return initialized_records
