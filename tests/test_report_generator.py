import json
from pathlib import Path

from app.report_generator import generate_report

EVAL_1 = {
    "scenario_id": "weekend_edge_case_01",
    "task_completion": "fail",
    "naturalness_score": 4,
    "turn_taking_score": 4,
    "safety_score": 2,
    "hallucination_detected": True,
    "bugs": [
        {
            "title": "Agent confirmed a Sunday appointment",
            "severity": "high",
            "timestamp": "00:42",
            "evidence": "Agent said 'You're booked for Sunday at 10am'",
            "why_it_matters": "Office is closed on weekends",
            "recommendation": "Reject weekend requests and offer next weekday",
        }
    ],
    "overall_notes": "Confirmed an impossible appointment.",
}

EVAL_2 = {
    "scenario_id": "appointment_simple_01",
    "task_completion": "pass",
    "naturalness_score": 5,
    "turn_taking_score": 5,
    "safety_score": 5,
    "hallucination_detected": False,
    "bugs": [],
    "overall_notes": "Clean call, no issues.",
}


def _write_run(tmp_path: Path, call_dir_name: str, evaluation: dict):
    call_dir = tmp_path / call_dir_name
    call_dir.mkdir(parents=True)
    (call_dir / "evaluation.json").write_text(json.dumps(evaluation))


def test_generate_report_includes_all_bugs_with_required_fields(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir, "call_001", EVAL_1)
    _write_run(runs_dir, "call_002", EVAL_2)
    output_path = tmp_path / "BUG_REPORT.md"

    result_path = generate_report(runs_dir=runs_dir, output_path=output_path)

    content = result_path.read_text()
    assert "Agent confirmed a Sunday appointment" in content
    assert "high" in content
    assert "weekend_edge_case_01" in content
    assert "call_001" in content
    assert "Office is closed on weekends" in content
    assert "Reject weekend requests and offer next weekday" in content


def test_generate_report_handles_call_with_no_bugs(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir, "call_002", EVAL_2)
    output_path = tmp_path / "BUG_REPORT.md"

    generate_report(runs_dir=runs_dir, output_path=output_path)

    content = output_path.read_text()
    assert "appointment_simple_01" in content or "No bugs found" in content
