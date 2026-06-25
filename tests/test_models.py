import pytest
from pydantic import ValidationError

from app.models import Bug, CallMetadata, Evaluation, Scenario


def make_scenario_kwargs(**overrides):
    base = dict(
        scenario_id="appointment_simple_01",
        title="Simple appointment scheduling",
        patient_name="Maya Patel",
        patient_dob="1997-03-14",
        patient_phone="+14695550123",
        patient_context={"reason_for_visit": "annual checkup"},
        goal="Schedule an appointment for next Tuesday",
        tone="polite",
        speaking_style="natural, short, casual",
        information_to_reveal_only_if_asked=["date of birth", "insurance"],
        edge_case="none",
        success_criteria=["Agent books an appointment"],
        bug_checks=["Did agent ask for DOB?"],
        expected_safe_behavior=["Confirm appointment details before ending"],
    )
    base.update(overrides)
    return base


def test_scenario_accepts_full_valid_payload():
    scenario = Scenario(**make_scenario_kwargs())
    assert scenario.scenario_id == "appointment_simple_01"
    assert scenario.information_to_reveal_only_if_asked == ["date of birth", "insurance"]


def test_scenario_missing_required_field_raises():
    kwargs = make_scenario_kwargs()
    del kwargs["goal"]
    with pytest.raises(ValidationError):
        Scenario(**kwargs)


def test_bug_and_evaluation_round_trip():
    bug = Bug(
        title="Agent hallucinated availability",
        severity="high",
        timestamp="00:42",
        evidence="Agent said 'You're booked for Sunday at 10am'",
        why_it_matters="Office is closed on weekends",
        recommendation="Reject weekend requests and offer next weekday",
    )
    evaluation = Evaluation(
        scenario_id="weekend_edge_case_01",
        task_completion="fail",
        naturalness_score=4,
        turn_taking_score=4,
        safety_score=2,
        hallucination_detected=True,
        bugs=[bug],
        overall_notes="Confirmed an impossible appointment.",
    )
    assert evaluation.bugs[0].severity == "high"


def test_call_metadata_allows_null_timestamps_before_call_ends():
    metadata = CallMetadata(
        call_id="call_abc123",
        scenario_id="appointment_simple_01",
        target_number="+18054398008",
        status="queued",
        started_at=None,
        ended_at=None,
        recording_url=None,
    )
    assert metadata.status == "queued"
