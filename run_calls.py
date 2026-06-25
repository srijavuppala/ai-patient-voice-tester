from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.caller import CallError, run_scenario_call
from app.config import get_settings
from app.evaluator import evaluate_call
from app.report_generator import generate_report
from app.scenarios import load_scenarios
from app.storage import next_call_dir, save_call

SCENARIOS_DIR = Path("scenarios")
RUNS_DIR = Path("runs")


def run_one_scenario(scenario, settings) -> None:
    print(f"[{scenario.scenario_id}] placing call...")
    try:
        call_result = run_scenario_call(scenario, settings)
    except CallError as exc:
        print(f"[{scenario.scenario_id}] FAILED: {exc}", file=sys.stderr)
        return

    call_dir = next_call_dir(base=RUNS_DIR)
    save_call(call_dir, scenario, call_result)
    print(f"[{scenario.scenario_id}] saved to {call_dir} (call_id={call_result['call_id']})")

    try:
        evaluation = evaluate_call(scenario, call_result["transcript"], settings)
        (call_dir / "evaluation.json").write_text(json.dumps(evaluation.model_dump(), indent=2))
        print(
            f"[{scenario.scenario_id}] evaluated: task_completion={evaluation.task_completion}, "
            f"bugs_found={len(evaluation.bugs)}"
        )
    except Exception as exc:  # noqa: BLE001 - log and continue, don't lose call artifacts
        print(f"[{scenario.scenario_id}] evaluation FAILED: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Place patient-simulator calls and evaluate the results.")
    parser.add_argument("--scenario", help="Run only the scenario with this scenario_id", default=None)
    args = parser.parse_args()

    settings = get_settings()
    scenarios = load_scenarios(SCENARIOS_DIR)

    if args.scenario:
        scenarios = [s for s in scenarios if s.scenario_id == args.scenario]
        if not scenarios:
            print(f"No scenario found with scenario_id={args.scenario!r}", file=sys.stderr)
            sys.exit(1)

    for scenario in scenarios:
        run_one_scenario(scenario, settings)

    report_path = generate_report(runs_dir=RUNS_DIR)
    print(f"Bug report written to {report_path}")


if __name__ == "__main__":
    main()
