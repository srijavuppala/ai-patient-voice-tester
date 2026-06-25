from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml

from app.models import Scenario


def next_call_dir(base: Path = Path("runs")) -> Path:
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    existing = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("call_")]
    numbers = [int(p.name.split("_")[1]) for p in existing if p.name.split("_")[1].isdigit()]
    next_number = max(numbers, default=0) + 1
    return base / f"call_{next_number:03d}"


def save_call(call_dir: Path, scenario: Scenario, call_result: dict) -> None:
    call_dir = Path(call_dir)
    call_dir.mkdir(parents=True, exist_ok=True)

    (call_dir / "scenario.yaml").write_text(yaml.safe_dump(scenario.model_dump()))
    (call_dir / "transcript.txt").write_text(call_result.get("transcript", ""))

    metadata = {
        "call_id": call_result.get("call_id"),
        "scenario_id": scenario.scenario_id,
        "status": call_result.get("status"),
        "started_at": call_result.get("started_at"),
        "ended_at": call_result.get("ended_at"),
        "recording_url": call_result.get("recording_url"),
    }
    (call_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    recording_url = call_result.get("recording_url")
    if recording_url:
        extension = "ogg" if recording_url.lower().endswith(".ogg") else "mp3"
        response = requests.get(recording_url, timeout=60)
        response.raise_for_status()
        (call_dir / f"recording.{extension}").write_bytes(response.content)
