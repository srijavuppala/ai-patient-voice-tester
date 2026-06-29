from pathlib import Path

from app.scenarios import load_scenarios

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def test_all_scenario_files_load_successfully():
    scenarios = load_scenarios(SCENARIOS_DIR)
    assert len(scenarios) == 12
    ids = {s.scenario_id for s in scenarios}
    assert len(ids) == 12, "scenario_id values must be unique"


def test_weekend_edge_case_flags_closed_office_in_bug_checks():
    scenarios = load_scenarios(SCENARIOS_DIR)
    weekend = next(s for s in scenarios if s.scenario_id == "weekend_edge_case_01")
    assert any("availab" in check.lower() or "hours" in check.lower() for check in weekend.bug_checks)
