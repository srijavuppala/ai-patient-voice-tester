import json
from pathlib import Path
from unittest.mock import patch

import yaml

from app.models import Scenario
from app.storage import next_call_dir, save_call


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


def test_next_call_dir_increments_across_existing_calls(tmp_path: Path):
    (tmp_path / "call_001").mkdir()
    (tmp_path / "call_002").mkdir()

    result = next_call_dir(base=tmp_path)

    assert result == tmp_path / "call_003"


def test_next_call_dir_starts_at_001_when_empty(tmp_path: Path):
    result = next_call_dir(base=tmp_path)
    assert result == tmp_path / "call_001"


def test_save_call_writes_all_artifacts(tmp_path: Path):
    call_dir = tmp_path / "call_001"
    scenario = make_scenario()
    call_result = {
        "call_id": "vapi_call_abc",
        "status": "ended",
        "started_at": "2026-06-24T10:00:00Z",
        "ended_at": "2026-06-24T10:02:30Z",
        "transcript": "AGENT: Hello, thanks for calling.\nPATIENT: Hi, I'd like to schedule an appointment.",
        "recording_url": "https://example.com/recording.mp3",
    }

    fake_audio = b"FAKE_MP3_BYTES"
    with patch("app.storage.requests.get") as mock_get:
        mock_get.return_value.content = fake_audio
        mock_get.return_value.raise_for_status = lambda: None
        save_call(call_dir, scenario, call_result)

    assert (call_dir / "scenario.yaml").exists()
    saved_scenario = yaml.safe_load((call_dir / "scenario.yaml").read_text())
    assert saved_scenario["scenario_id"] == "appointment_simple_01"

    assert (call_dir / "transcript.txt").read_text() == call_result["transcript"]

    metadata = json.loads((call_dir / "metadata.json").read_text())
    assert metadata["call_id"] == "vapi_call_abc"
    assert metadata["scenario_id"] == "appointment_simple_01"

    assert (call_dir / "recording.mp3").read_bytes() == fake_audio
