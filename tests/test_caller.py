import pytest
import responses

from app.caller import ALLOWED_TARGET_NUMBER, CallError, place_call, poll_call
from app.config import Settings
from app.models import Scenario


def make_scenario():
    return Scenario(
        scenario_id="appointment_simple_01",
        title="Simple appointment scheduling",
        patient_name="Maya Patel",
        patient_dob="1997-03-14",
        patient_phone="+14695550123",
        patient_context={"reason_for_visit": "annual checkup"},
        goal="Schedule an appointment",
        tone="friendly",
        speaking_style="short",
        information_to_reveal_only_if_asked=["date of birth"],
        edge_case="none",
        success_criteria=["booked"],
        bug_checks=["check1"],
        expected_safe_behavior=["behavior1"],
    )


def make_settings():
    return Settings(
        vapi_api_key="test-key",
        vapi_phone_number_id="phone-id-123",
        anthropic_api_key="anthropic-key",
    )


def test_place_call_rejects_disallowed_number():
    scenario = make_scenario()
    settings = make_settings()

    with pytest.raises(CallError, match="only call"):
        place_call(scenario, settings, target_number="+15555555555")


@responses.activate
def test_place_call_posts_to_vapi_and_returns_call_id():
    scenario = make_scenario()
    settings = make_settings()
    responses.add(
        responses.POST,
        "https://api.vapi.ai/call",
        json={"id": "vapi_call_abc123", "status": "queued"},
        status=201,
    )

    call_id = place_call(scenario, settings, target_number=ALLOWED_TARGET_NUMBER)

    assert call_id == "vapi_call_abc123"
    sent_body = responses.calls[0].request.body.decode()
    assert "phone-id-123" in sent_body
    assert ALLOWED_TARGET_NUMBER in sent_body


@responses.activate
def test_poll_call_returns_final_result_once_ended():
    settings = make_settings()
    responses.add(
        responses.GET,
        "https://api.vapi.ai/call/vapi_call_abc123",
        json={"id": "vapi_call_abc123", "status": "in-progress"},
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.vapi.ai/call/vapi_call_abc123",
        json={
            "id": "vapi_call_abc123",
            "status": "ended",
            "startedAt": "2026-06-24T10:00:00Z",
            "endedAt": "2026-06-24T10:02:00Z",
            "transcript": "AGENT: Hi.\nPATIENT: Hi, I'd like an appointment.",
            "recordingUrl": "https://example.com/rec.mp3",
        },
        status=200,
    )

    result = poll_call("vapi_call_abc123", settings, interval=0, timeout=5)

    assert result["status"] == "ended"
    assert result["call_id"] == "vapi_call_abc123"
    assert result["transcript"].startswith("AGENT: Hi.")
    assert result["recording_url"] == "https://example.com/rec.mp3"


@responses.activate
def test_poll_call_times_out_if_never_ends():
    settings = make_settings()
    responses.add(
        responses.GET,
        "https://api.vapi.ai/call/vapi_call_abc123",
        json={"id": "vapi_call_abc123", "status": "in-progress"},
        status=200,
    )

    with pytest.raises(CallError, match="timed out"):
        poll_call("vapi_call_abc123", settings, interval=0, timeout=0)
