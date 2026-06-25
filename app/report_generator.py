from __future__ import annotations

import json
from pathlib import Path

from app.models import Evaluation


def _load_evaluations(runs_dir: Path) -> list[tuple[str, Evaluation]]:
    results = []
    for call_dir in sorted(Path(runs_dir).iterdir()):
        eval_path = call_dir / "evaluation.json"
        if eval_path.exists():
            data = json.loads(eval_path.read_text())
            results.append((call_dir.name, Evaluation(**data)))
    return results


def generate_report(runs_dir: Path = Path("runs"), output_path: Path = Path("BUG_REPORT.md")) -> Path:
    evaluations = _load_evaluations(runs_dir)

    lines = ["# Bug Report", ""]
    any_bugs = False

    for call_name, evaluation in evaluations:
        if not evaluation.bugs:
            continue
        for bug in evaluation.bugs:
            any_bugs = True
            lines.append(f"## {bug.title}")
            lines.append(f"- **Severity:** {bug.severity}")
            lines.append(f"- **Scenario:** {evaluation.scenario_id}")
            lines.append(f"- **Call:** {call_name}")
            lines.append(f"- **Timestamp:** {bug.timestamp}")
            lines.append(f"- **What happened:** {bug.evidence}")
            lines.append(f"- **Why it matters:** {bug.why_it_matters}")
            lines.append(f"- **Recommendation:** {bug.recommendation}")
            lines.append("")

    if not any_bugs:
        lines.append("No bugs found across the evaluated calls.")
        lines.append("")

    lines.append("## All Calls Summary")
    for call_name, evaluation in evaluations:
        lines.append(
            f"- {call_name} ({evaluation.scenario_id}): task_completion={evaluation.task_completion}, "
            f"naturalness={evaluation.naturalness_score}, safety={evaluation.safety_score}"
        )

    output_path = Path(output_path)
    output_path.write_text("\n".join(lines))
    return output_path
