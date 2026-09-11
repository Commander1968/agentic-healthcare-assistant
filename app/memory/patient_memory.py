import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from pydantic import BaseModel, Field


class MemoryTurn(BaseModel):
    user_request: str
    assistant_response: str


class PatientMemory(BaseModel):
    patient_id: str

    turns: List[MemoryTurn] = Field(
        default_factory=list
    )

    last_specialty: Optional[str] = None
    last_appointment_id: Optional[str] = None


PATIENT_MEMORY_STORE_SCHEMA_VERSION = 1
DEFAULT_PATIENT_MEMORY_STORE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "patient_memory.json"
)


def resolve_patient_memory_store_path(
    store_path: str | Path | None = None,
) -> Path:
    if store_path is not None:
        return Path(store_path)

    configured_path = os.getenv("PATIENT_MEMORY_STORE_PATH")
    if configured_path:
        return Path(configured_path)

    return DEFAULT_PATIENT_MEMORY_STORE_PATH


def save_patient_memories(
    memories: Iterable[PatientMemory],
    store_path: str | Path,
) -> Path:
    destination = Path(store_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PATIENT_MEMORY_STORE_SCHEMA_VERSION,
        "patient_memories": [
            memory.model_dump(mode="json")
            for memory in memories
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


def load_patient_memories(
    store_path: str | Path,
) -> Dict[str, PatientMemory]:
    source = Path(store_path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("Patient-memory store must contain a JSON object.")
    if payload.get("schema_version") != PATIENT_MEMORY_STORE_SCHEMA_VERSION:
        raise ValueError("Patient-memory store schema version is unsupported.")

    serialized_memories = payload.get("patient_memories")
    if not isinstance(serialized_memories, list):
        raise ValueError("Patient-memory store is missing patient_memories.")

    memories = [
        PatientMemory.model_validate(memory)
        for memory in serialized_memories
    ]
    if len({memory.patient_id for memory in memories}) != len(memories):
        raise ValueError("Patient-memory store contains duplicate patient IDs.")

    return {
        memory.patient_id: memory
        for memory in memories
    }


class PatientMemoryStore:
    """
    Patient-scoped bounded memory store for the prototype.

    Memory is keyed by patient_id and retains only a bounded
    number of recent interaction turns. Supplying store_path
    enables versioned, atomic persistence across restarts.
    """

    def __init__(
        self,
        max_turns: int = 5,
        store_path: str | Path | None = None,
    ):
        self.max_turns = max_turns
        self.store_path = Path(store_path) if store_path is not None else None

        if self.store_path is not None and self.store_path.exists():
            self._store = load_patient_memories(self.store_path)
        else:
            self._store: Dict[str, PatientMemory] = {}

    def _persist(self) -> None:
        if self.store_path is not None:
            save_patient_memories(self._store.values(), self.store_path)

    def remember(
        self,
        patient_id: str,
        user_request: str,
        assistant_response: str,
        specialty: Optional[str] = None,
        appointment_id: Optional[str] = None,
    ) -> PatientMemory:
        original_store = {
            key: value.model_copy(deep=True)
            for key, value in self._store.items()
        }
        memory = self._store.get(
            patient_id,
            PatientMemory(patient_id=patient_id),
        ).model_copy(deep=True)

        memory.turns.append(
            MemoryTurn(
                user_request=user_request,
                assistant_response=assistant_response,
            )
        )

        memory.turns = memory.turns[-self.max_turns:]

        if specialty is not None:
            memory.last_specialty = specialty

        if appointment_id is not None:
            memory.last_appointment_id = appointment_id

        self._store[patient_id] = memory

        try:
            self._persist()
        except Exception:
            self._store = original_store
            raise

        return memory.model_copy(deep=True)

    def recall(
        self,
        patient_id: str,
    ) -> Optional[PatientMemory]:
        memory = self._store.get(patient_id)

        if memory is None:
            return None

        return memory.model_copy(deep=True)

    def clear(
        self,
        patient_id: str,
    ) -> bool:
        if patient_id not in self._store:
            return False

        original_store = {
            key: value.model_copy(deep=True)
            for key, value in self._store.items()
        }
        del self._store[patient_id]

        try:
            self._persist()
        except Exception:
            self._store = original_store
            raise

        return True

    def clear_all(self) -> None:
        original_store = {
            key: value.model_copy(deep=True)
            for key, value in self._store.items()
        }
        self._store.clear()

        try:
            self._persist()
        except Exception:
            self._store = original_store
            raise


patient_memory_store = PatientMemoryStore(
    store_path=resolve_patient_memory_store_path()
)
