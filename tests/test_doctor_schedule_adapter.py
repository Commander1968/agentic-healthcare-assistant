from copy import deepcopy

import pytest

from app.agents.healthcare_graph import book_appointment_node, find_doctors
from app.integrations.doctor_schedule import (
    DoctorScheduleService,
    InMemoryDoctorScheduleAdapter,
)
from app.models.appointment import Appointment
from app.models.workflow_state import WorkflowState
from data.mock_data import doctors


def test_in_memory_adapter_satisfies_doctor_schedule_protocol():
    adapter = InMemoryDoctorScheduleAdapter(deepcopy(doctors))

    assert isinstance(adapter, DoctorScheduleService)


def test_adapter_finds_doctors_and_books_an_available_slot():
    adapter = InMemoryDoctorScheduleAdapter(deepcopy(doctors))
    matches = adapter.find_doctors_by_specialty("Nephrology")
    doctor = matches[0]
    selected_slot = doctor.available_slots[0]

    appointment = adapter.book_appointment(
        appointment_id="A001",
        patient_id="P001",
        doctor=doctor,
        appointment_time=selected_slot,
        reason="Nephrology consultation",
    )

    assert appointment.doctor_id == doctor.doctor_id
    assert appointment.appointment_time == selected_slot
    assert selected_slot not in doctor.available_slots


def test_adapter_rejects_an_unavailable_slot():
    adapter = InMemoryDoctorScheduleAdapter(deepcopy(doctors))
    doctor = adapter.find_doctors_by_specialty("Nephrology")[0]

    with pytest.raises(ValueError, match="not available"):
        adapter.book_appointment(
            appointment_id="A001",
            patient_id="P001",
            doctor=doctor,
            appointment_time="2099-01-01T00:00:00",
            reason="Nephrology consultation",
        )


class SpyDoctorSchedule:
    def __init__(self):
        self.doctor = deepcopy(doctors[0])
        self.lookup_specialty = None
        self.booking_arguments = None

    def find_doctors_by_specialty(self, specialty: str):
        self.lookup_specialty = specialty
        return [self.doctor]

    def book_appointment(
        self,
        appointment_id,
        patient_id,
        doctor,
        appointment_time,
        reason,
    ):
        self.booking_arguments = {
            "appointment_id": appointment_id,
            "patient_id": patient_id,
            "doctor": doctor,
            "appointment_time": appointment_time,
            "reason": reason,
        }
        return Appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor.doctor_id,
            appointment_time=appointment_time,
            reason=reason,
        )


def test_scheduling_graph_nodes_use_injected_adapter_boundary():
    spy = SpyDoctorSchedule()
    state = WorkflowState(
        patient_id="P001",
        requested_specialty="Nephrology",
        reason="Nephrology consultation",
        appointment_requested=True,
    )

    state = find_doctors(state, spy)
    state = book_appointment_node(state, spy)

    assert spy.lookup_specialty == "Nephrology"
    assert spy.booking_arguments["doctor"] is spy.doctor
    assert spy.booking_arguments["appointment_time"] == spy.doctor.available_slots[0]
    assert state.appointment.appointment_id == "A001"
