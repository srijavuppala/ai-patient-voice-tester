from pathlib import Path

import pytest
import yaml

from app.scenarios import ScenarioLoadError, load_scenarios

VALID_SCENARIO = {
    "scenario_id": "appointment_simple_01",
    "title": "Simple appointment scheduling",
    "patient_name": "Maya Patel",
    "patient_dob": "1997-03-14",
    "patient_phone": "+14695550123",
    "patient_context": {"reason_for_visit": "annual checkup"},
    "goal": "Schedule an appointment for next Tuesday",
    "tone": "polite",
    "speaking_style": "natural, short, casual",
    "information_to_reveal_only_if_asked": ["date of birth"],
    "edge_case": "none",
    "success_criteria": ["Agent books an appointment"],
    "bug_checks": ["Did agent ask for DOB?"],
    "expected_safe_behavior": ["Confirm details before ending"],
}


def test_load_scenarios_reads_all_yaml_files(tmp_path: Path):
    (tmp_path / "appointment_simple.yaml").write_text(yaml.safe_dump(VALID_SCENARIO))
    other = dict(VALID_SCENARIO, scenario_id="refill_01", title="Refill request")
    (tmp_path / "refill.yaml").write_text(yaml.safe_dump(other))

    scenarios = load_scenarios(tmp_path)

    assert len(scenarios) == 2
    ids = {s.scenario_id for s in scenarios}
    assert ids == {"appointment_simple_01", "refill_01"}


def test_load_scenarios_raises_with_filename_on_missing_field(tmp_path: Path):
    broken = dict(VALID_SCENARIO)
    del broken["goal"]
    (tmp_path / "broken.yaml").write_text(yaml.safe_dump(broken))

    with pytest.raises(ScenarioLoadError, match="broken.yaml"):
        load_scenarios(tmp_path)
