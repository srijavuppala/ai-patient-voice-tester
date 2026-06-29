from __future__ import annotations

import json
import re
from pathlib import Path


def simple_yaml_parse(text: str) -> dict:
    """Parse simple YAML (no nested lists/objects, just key: value)."""
    result = {}
    current_key = None
    current_list = None
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list is not None:
                current_list.append(stripped[2:].strip())
        elif ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "":
                current_key = key
                current_list = []
                result[key] = current_list
            else:
                # Remove surrounding quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                result[key] = val
                current_key = None
                current_list = None
    return result


def load_calls(runs_dir: Path = Path("runs")) -> list[dict]:
    calls = []
    for call_dir in sorted(runs_dir.iterdir()):
        if not call_dir.is_dir() or not call_dir.name.startswith("call_"):
            continue

        transcript_path = call_dir / "transcript.txt"
        eval_path = call_dir / "evaluation.json"
        meta_path = call_dir / "metadata.json"
        scenario_path = call_dir / "scenario.yaml"
        recording_path = call_dir / "recording.mp3"
        if not recording_path.exists():
            recording_path = call_dir / "recording.ogg"

        if not transcript_path.exists() or not eval_path.exists():
            continue

        call_data = {
            "dir": call_dir.name,
            "transcript": transcript_path.read_text(),
            "evaluation": json.loads(eval_path.read_text()),
            "metadata": json.loads(meta_path.read_text()) if meta_path.exists() else {},
            "scenario": simple_yaml_parse(scenario_path.read_text()) if scenario_path.exists() else {},
            "has_recording": recording_path.exists(),
            "recording_filename": recording_path.name if recording_path.exists() else None,
        }
        calls.append(call_data)
    return calls


def load_scenarios(scenarios_dir: Path = Path("scenarios")) -> dict[str, dict]:
    scenarios = {}
    for path in sorted(scenarios_dir.glob("*.yaml")):
        data = simple_yaml_parse(path.read_text())
        scenarios[data.get("scenario_id", path.stem)] = data
    return scenarios


def parse_bug_report(report_path: Path = Path("BUG_REPORT.md")) -> dict[str, list[dict]]:
    """Parse BUG_REPORT.md and map bugs by (call_dir, scenario_id)."""
    text = report_path.read_text()
    bugs_by_call: dict[str, list[dict]] = {}

    # Find all bug sections
    bug_blocks = re.split(r"\n### \d+\.\s", text)
    for block in bug_blocks[1:]:  # skip preamble
        lines = block.strip().split("\n")
        if not lines:
            continue

        title = lines[0].strip()
        bug = {"title": title, "severity": "", "call": "", "scenario": "", "evidence": "", "why": "", "recommendation": ""}

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("- **Severity:**"):
                bug["severity"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("- **Scenario:**"):
                bug["scenario"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Call:**"):
                call_ref = line.split(":", 1)[1].strip()
                # Extract call dir like call_001 from "call_001/transcript.txt"
                match = re.search(r"(call_\d+)", call_ref)
                if match:
                    bug["call"] = match.group(1)
            elif line.startswith("- **What happened:**") or line.startswith("- **What happened**"):
                bug["evidence"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("- **Why it matters:**") or line.startswith("- **Why it matters**"):
                bug["why"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("- **Recommendation:**") or line.startswith("- **Recommendation**"):
                bug["recommendation"] = line.split(":", 1)[1].strip() if ":" in line else ""

        if bug["call"]:
            bugs_by_call.setdefault(bug["call"], []).append(bug)

    return bugs_by_call


def severity_class(severity: str) -> str:
    return {"high": "severity-high", "medium": "severity-medium", "low": "severity-low"}.get(severity.lower(), "severity-low")


def completion_class(tc: str) -> str:
    return {"pass": "pass", "fail": "fail", "partial": "partial"}.get(tc.lower(), "partial")


def transcript_html(transcript: str, call_bugs: list[dict]) -> str:
    lines = transcript.strip().split("\n")
    html_parts = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if line.startswith("AI:"):
            speaker = "AI"
            text = line[3:].strip()
            css = "transcript-line ai-line"
        elif line.startswith("User:"):
            speaker = "Agent"
            text = line[5:].strip()
            css = "transcript-line agent-line"
        else:
            speaker = "?"
            text = line.strip()
            css = "transcript-line"

        # Check if any bug evidence appears in this line
        line_bugs = []
        for bug in call_bugs:
            if bug.get("evidence") and bug["evidence"].lower() in text.lower():
                line_bugs.append(bug)
            # Also check by line number in timestamp like "line 6" or "line 6-7"
            ts = bug.get("timestamp", "")
            if f"line {i}" in ts or f"line {i}," in ts or f"line {i}-" in ts:
                line_bugs.append(bug)

        bug_badges = ""
        for bug in line_bugs:
            escaped_why = bug["why"].replace('"', "'") if bug["why"] else ""
            bug_badges += f'<span class="bug-badge {severity_class(bug["severity"])}" title="{escaped_why}">🐛 {bug["title"]}</span>'

        html_parts.append(f'<div class="{css}"><span class="speaker">{speaker}</span><span class="text">{text}{bug_badges}</span></div>')

    return "\n".join(html_parts)


def generate_dashboard(output_path: Path = Path("dashboard/index.html")) -> None:
    calls = load_calls()
    scenarios = load_scenarios()
    bugs_by_call = parse_bug_report()

    total = len(calls)
    passed = sum(1 for c in calls if c["evaluation"].get("task_completion") == "pass")
    failed = sum(1 for c in calls if c["evaluation"].get("task_completion") == "fail")
    partial = sum(1 for c in calls if c["evaluation"].get("task_completion") == "partial")
    total_bugs = sum(len(c["evaluation"].get("bugs", [])) for c in calls)

    call_cards = []
    for call in calls:
        call_dir = call["dir"]
        eval_data = call["evaluation"]
        scenario_id = eval_data.get("scenario_id", "")
        scenario = scenarios.get(scenario_id, {})
        call_bugs = bugs_by_call.get(call_dir, [])

        tc = eval_data.get("task_completion", "partial")
        nat = eval_data.get("naturalness_score", 0)
        turn = eval_data.get("turn_taking_score", 0)
        safe = eval_data.get("safety_score", 0)
        hall = "🚨" if eval_data.get("hallucination_detected") else "✅"

        bug_list_html = ""
        if call_bugs:
            bug_items = "\n".join(
                f'<li class="{severity_class(b["severity"])}"><strong>{b["severity"].upper()}</strong>: {b["title"]}</li>'
                for b in call_bugs
            )
            bug_list_html = f'<ul class="bug-list">{bug_items}</ul>'
        else:
            bug_list_html = '<p class="no-bugs">✅ No bugs found</p>'

        recording_html = ""
        if call["has_recording"] and call["recording_filename"]:
            rel_path = f"../runs/{call_dir}/{call['recording_filename']}"
            recording_html = f'<audio controls class="audio-player"><source src="{rel_path}" type="audio/mpeg"></audio>'
        else:
            recording_html = '<p class="no-recording">🚫 No recording available</p>'

        transcript_html_str = transcript_html(call["transcript"], call_bugs)

        card = f"""
<div class="call-card" id="{call_dir}">
  <div class="call-header">
    <div class="call-title">
      <span class="call-id">{call_dir}</span>
      <span class="scenario-tag">{scenario_id}</span>
      <span class="completion-badge {completion_class(tc)}">{tc.upper()}</span>
    </div>
    <div class="scores">
      <span class="score" title="Naturalness">🎭 {nat}/5</span>
      <span class="score" title="Turn-taking">🔄 {turn}/5</span>
      <span class="score" title="Safety">🛡️ {safe}/5</span>
      <span class="score" title="Hallucination">{hall}</span>
    </div>
  </div>
  <div class="scenario-info">
    <strong>{scenario.get("title", scenario_id)}</strong> — {scenario.get("goal", "")}
    <div class="edge-case">Edge case: {scenario.get("edge_case", "none")}</div>
  </div>
  {recording_html}
  <div class="transcript-container">
    {transcript_html_str}
  </div>
  <div class="bugs-section">
    <h4>Bugs Found ({len(call_bugs)})</h4>
    {bug_list_html}
  </div>
</div>
"""
        call_cards.append(card)

    # Build all scenarios table
    scenario_rows = []
    for sid, s in scenarios.items():
        call_for_scenario = next((c for c in calls if c["evaluation"].get("scenario_id") == sid), None)
        if call_for_scenario:
            tc = call_for_scenario["evaluation"].get("task_completion", "—")
            nat = call_for_scenario["evaluation"].get("naturalness_score", "—")
            safe = call_for_scenario["evaluation"].get("safety_score", "—")
            bugs = len(call_for_scenario["evaluation"].get("bugs", []))
            scenario_rows.append(f"""
<tr>
  <td><a href="#{call_for_scenario['dir']}">{sid}</a></td>
  <td>{s.get('title', '')}</td>
  <td class="{completion_class(tc)}">{tc.upper()}</td>
  <td>{nat}/5</td>
  <td>{safe}/5</td>
  <td>{bugs}</td>
</tr>
""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Patient Voice Tester — Dashboard</title>
<style>
:root {{
  --bg: #0f172a;
  --card: #1e293b;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --pass: #22c55e;
  --fail: #ef4444;
  --partial: #f59e0b;
  --high: #ef4444;
  --medium: #f59e0b;
  --low: #22c55e;
  --ai-bg: #1e3a5f;
  --agent-bg: #2d3a1e;
  --border: #334155;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  padding: 2rem 1rem;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 2rem; margin-bottom: 0.5rem; color: var(--accent); }}
.subtitle {{ color: var(--muted); margin-bottom: 2rem; }}
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}}
.stat-card {{
  background: var(--card);
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  border: 1px solid var(--border);
}}
.stat-value {{ font-size: 2.5rem; font-weight: 700; }}
.stat-label {{ color: var(--muted); font-size: 0.9rem; margin-top: 0.25rem; }}
.stat-pass {{ color: var(--pass); }}
.stat-fail {{ color: var(--fail); }}
.stat-partial {{ color: var(--partial); }}
.stat-bugs {{ color: var(--high); }}
.section {{ margin-bottom: 3rem; }}
.section h2 {{ margin-bottom: 1rem; color: var(--accent); font-size: 1.5rem; }}
.scenarios-table {{
  width: 100%;
  border-collapse: collapse;
  background: var(--card);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
}}
.scenarios-table th, .scenarios-table td {{
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}}
.scenarios-table th {{
  background: rgba(56, 189, 248, 0.1);
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent);
}}
.scenarios-table a {{ color: var(--accent); text-decoration: none; }}
.scenarios-table a:hover {{ text-decoration: underline; }}
.call-card {{
  background: var(--card);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid var(--border);
}}
.call-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}}
.call-title {{ display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }}
.call-id {{ font-size: 1.25rem; font-weight: 700; color: var(--accent); }}
.scenario-tag {{
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent);
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
}}
.completion-badge {{
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.completion-badge.pass {{ background: rgba(34, 197, 94, 0.2); color: var(--pass); }}
.completion-badge.fail {{ background: rgba(239, 68, 68, 0.2); color: var(--fail); }}
.completion-badge.partial {{ background: rgba(245, 158, 11, 0.2); color: var(--partial); }}
.scores {{ display: flex; gap: 0.75rem; flex-wrap: wrap; }}
.score {{
  background: rgba(255,255,255,0.05);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.85rem;
  color: var(--muted);
}}
.scenario-info {{ margin-bottom: 1rem; color: var(--muted); }}
.scenario-info .edge-case {{ font-size: 0.85rem; margin-top: 0.25rem; font-style: italic; }}
.audio-player {{ width: 100%; margin-bottom: 1rem; border-radius: 8px; }}
.no-recording {{ color: var(--muted); font-size: 0.9rem; font-style: italic; }}
.transcript-container {{
  background: rgba(0,0,0,0.2);
  border-radius: 12px;
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 1rem;
}}
.transcript-line {{
  display: flex;
  gap: 0.75rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}}
.transcript-line:last-child {{ border-bottom: none; }}
.ai-line {{ background: var(--ai-bg); border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.25rem; }}
.agent-line {{ background: var(--agent-bg); border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.25rem; }}
.speaker {{
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 60px;
  color: var(--muted);
  flex-shrink: 0;
  padding-top: 0.15rem;
}}
.ai-line .speaker {{ color: var(--accent); }}
.agent-line .speaker {{ color: var(--pass); }}
.text {{ flex: 1; font-size: 0.95rem; }}
.bug-badge {{
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: help;
}}
.bug-badge.severity-high {{ background: rgba(239, 68, 68, 0.2); color: var(--high); }}
.bug-badge.severity-medium {{ background: rgba(245, 158, 11, 0.2); color: var(--medium); }}
.bug-badge.severity-low {{ background: rgba(34, 197, 94, 0.2); color: var(--low); }}
.bugs-section h4 {{ margin-bottom: 0.5rem; color: var(--text); }}
.bug-list {{ list-style: none; }}
.bug-list li {{
  padding: 0.4rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 0.9rem;
}}
.bug-list li:last-child {{ border-bottom: none; }}
.no-bugs {{ color: var(--pass); font-size: 0.9rem; }}
.scenarios-table td.pass {{ color: var(--pass); font-weight: 600; }}
.scenarios-table td.fail {{ color: var(--fail); font-weight: 600; }}
.scenarios-table td.partial {{ color: var(--partial); font-weight: 600; }}
@media (max-width: 768px) {{
  .call-header {{ flex-direction: column; align-items: flex-start; }}
  .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<div class="container">
  <h1>🎙️ AI Patient Voice Tester</h1>
  <p class="subtitle">Automated healthcare AI agent testing dashboard — 12 real voice calls, transcripts, recordings, and bug findings</p>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value">{total}</div>
      <div class="stat-label">Total Calls</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-pass">{passed}</div>
      <div class="stat-label">Passed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-fail">{failed}</div>
      <div class="stat-label">Failed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-partial">{partial}</div>
      <div class="stat-label">Partial</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-bugs">{total_bugs}</div>
      <div class="stat-label">Bugs Found</div>
    </div>
  </div>

  <div class="section">
    <h2>📋 All Scenarios</h2>
    <table class="scenarios-table">
      <thead>
        <tr><th>Scenario</th><th>Title</th><th>Result</th><th>Naturalness</th><th>Safety</th><th>Bugs</th></tr>
      </thead>
      <tbody>
        {''.join(scenario_rows)}
      </tbody>
    </table>
  </div>

  <div class="section">
    <h2>📞 Call Details</h2>
    {''.join(call_cards)}
  </div>
</div>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Dashboard generated: {output_path.resolve()}")


if __name__ == "__main__":
    generate_dashboard()
