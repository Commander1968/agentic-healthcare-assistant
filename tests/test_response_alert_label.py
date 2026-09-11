from types import SimpleNamespace

from app.agents.response_synthesizer import synthesize_response
from app.models.medical_record import MedicalRecord
from app.models.workflow_state import WorkflowState


ALERT = "Demo alert: Medication allergy information requires verification."


def alert_state() -> WorkflowState:
    return WorkflowState(
        patient_id="P001",
        appointment_requested=False,
        medical_record=MedicalRecord(
            record_id="R001",
            patient_id="P001",
            alerts=[ALERT],
        ),
    )


def test_synthesizer_normalizes_alerts_label(monkeypatch):
    monkeypatch.setattr(
        "app.agents.response_synthesizer.client.responses.create",
        lambda **_kwargs: SimpleNamespace(
            output_text=f"Patient summary\n\nAlerts: {ALERT}"
        ),
    )

    response = synthesize_response(alert_state())

    assert "Relevant Alerts:" in response
    assert "\n\nAlerts:" not in response
    assert ALERT in response


def test_synthesizer_appends_required_label_when_model_omits_alert_section(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.agents.response_synthesizer.client.responses.create",
        lambda **_kwargs: SimpleNamespace(output_text="Patient summary"),
    )

    response = synthesize_response(alert_state())

    assert response.endswith(f"Relevant Alerts: {ALERT}")

